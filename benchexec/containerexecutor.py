# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import argparse
import errno
import glob
import logging
import os
import collections
import shutil
import pickle
import select
import shlex
import signal
import socket
import subprocess
import sys
import tempfile
import traceback

from benchexec import __version__
from benchexec import baseexecutor
from benchexec import BenchExecException
from benchexec.cgroups import Cgroups
from benchexec import container
from benchexec import libc
from benchexec import util
from benchexec.container import (
    DIR_MODES,
    DIR_HIDDEN,
    DIR_READ_ONLY,
    DIR_OVERLAY,
    DIR_FULL_ACCESS,
    NATIVE_CLONE_CALLBACK_SUPPORTED,
)

sys.dont_write_bytecode = True  # prevent creation of .pyc files

_MAX_RESULT_FILE_LOG_COUNT = 1000
"""How many result files to log at most."""


def add_basic_container_args(argument_parser):
    argument_parser.add_argument(
        "--network-access",
        action="store_true",
        help="allow process to use network communication",
    )
    argument_parser.add_argument(
        "--no-tmpfs",
        dest="tmpfs",
        action="store_false",
        help="Store temporary files (e.t., tool output files) on the actual file system"
        ' instead of a tmpfs ("RAM disk") that is included in the memory limit',
    )
    argument_parser.add_argument(
        "--keep-system-config",
        dest="container_system_config",
        action="store_false",
        help="do not use a special minimal configuration for local user and"
        " host lookups inside the container",
    )
    argument_parser.add_argument(
        "--keep-tmp",
        action="store_true",
        help="do not use a private /tmp for process (same as '--full-access-dir /tmp')",
    )
    argument_parser.add_argument(
        "--hidden-dir",
        metavar="DIR",
        action="append",
        default=[],
        help="hide this directory by mounting an empty directory over it "
        "(default for '/tmp' and '/run')",
    )
    argument_parser.add_argument(
        "--read-only-dir",
        metavar="DIR",
        action="append",
        default=[],
        help="make this directory visible read-only in the container",
    )
    argument_parser.add_argument(
        "--overlay-dir",
        metavar="DIR",
        action="append",
        default=[],
        help="mount an overlay filesystem over this directory "
        "that redirects all write accesses to temporary files (default for '/')",
    )
    argument_parser.add_argument(
        "--full-access-dir",
        metavar="DIR",
        action="append",
        default=[],
        help="give full access (read/write) to this host directory"
        " to processes inside container",
    )


def handle_basic_container_args(options, parser=None):
    """Handle the options specified by add_basic_container_args().
    @return: a dict that can be used as kwargs for the ContainerExecutor constructor
    """
    dir_modes = {}
    error_fn = parser.error if parser else sys.exit

    def handle_dir_mode(path, mode):
        path = os.path.abspath(path)
        if not os.path.isdir(path):
            error_fn(
                f"Cannot specify directory mode for '{path}' "
                f"because it does not exist or is no directory."
            )
        if path in dir_modes:
            error_fn(f"Cannot specify multiple directory modes for '{path}'.")
        if path == "/proc":
            error_fn(
                "Cannot specify directory mode for /proc, "
                "this directory is handled specially."
            )
        dir_modes[path] = mode

    for path in options.hidden_dir:
        handle_dir_mode(path, DIR_HIDDEN)
    for path in options.read_only_dir:
        handle_dir_mode(path, DIR_READ_ONLY)
    for path in options.overlay_dir:
        handle_dir_mode(path, DIR_OVERLAY)
    for path in options.full_access_dir:
        handle_dir_mode(path, DIR_FULL_ACCESS)

    if options.keep_tmp:
        if "/tmp" in dir_modes and not dir_modes["/tmp"] == DIR_FULL_ACCESS:
            error_fn("Cannot specify both --keep-tmp and --hidden-dir /tmp.")
        dir_modes["/tmp"] = DIR_FULL_ACCESS
    elif "/tmp" not in dir_modes:
        dir_modes["/tmp"] = DIR_HIDDEN

    if "/" not in dir_modes:
        dir_modes["/"] = DIR_OVERLAY
    if "/run" not in dir_modes:
        dir_modes["/run"] = DIR_HIDDEN

    if options.container_system_config:
        if options.network_access:
            logging.warning(
                "The container configuration disables DNS, "
                "host lookups will fail despite --network-access. "
                "Consider using --keep-system-config."
            )
    else:
        # /etc/resolv.conf is necessary for DNS lookups and on many systems is a symlink
        # to /run/resolvconf/resolv.conf or /run/systemd/resolve/sub-resolve.conf,
        # so we keep that directory accessible as well.
        if "/run/resolvconf" not in dir_modes and os.path.isdir("/run/resolvconf"):
            dir_modes["/run/resolvconf"] = DIR_READ_ONLY
        if "/run/systemd/resolve" not in dir_modes and os.path.isdir(
            "/run/systemd/resolve"
        ):
            dir_modes["/run/systemd/resolve"] = DIR_READ_ONLY

    return {
        "network_access": options.network_access,
        "container_tmpfs": options.tmpfs,
        "container_system_config": options.container_system_config,
        "dir_modes": dir_modes,
    }


def add_container_output_args(argument_parser):
    """Define command-line arguments for output of a container (result files).
    @param argument_parser: an argparse parser instance
    """
    argument_parser.add_argument(
        "--output-directory",
        metavar="DIR",
        default="output.files",
        help="target directory for result files (default: './output.files')",
    )
    argument_parser.add_argument(
        "--result-files",
        metavar="PATTERN",
        action="append",
        default=[],
        help="pattern for specifying which result files should be copied"
        " to the output directory (default: '.')",
    )


def handle_container_output_args(options, parser):
    """Handle the options specified by add_container_output_args().
    @return: a dict that can be used as kwargs for the ContainerExecutor.execute_run()
    """
    if options.result_files:
        result_files_patterns = [os.path.normpath(p) for p in options.result_files if p]
        for pattern in result_files_patterns:
            if pattern.startswith(".."):
                parser.error(f"Invalid relative result-files pattern '{pattern}'.")
    else:
        result_files_patterns = ["."]

    output_dir = options.output_directory
    if os.path.exists(output_dir) and not os.path.isdir(output_dir):
        parser.error(
            f"Output directory '{output_dir}' must not refer to an existing file."
        )
    return {"output_dir": output_dir, "result_files_patterns": result_files_patterns}


def main(argv=None):
    """
    A simple command-line interface for the containerexecutor module of BenchExec.
    """
    if argv is None:
        argv = sys.argv

    # parse options
    parser = argparse.ArgumentParser(
        fromfile_prefix_chars="@",
        description="""Execute a command inside a simple container, i.e., partially
            isolated from the host. Command-line parameters can additionally be read
            from a file if file name prefixed with '@' is given as argument.
            Part of BenchExec: https://github.com/sosy-lab/benchexec/""",
    )
    parser.add_argument(
        "--dir",
        metavar="DIR",
        help="working directory for executing the command"
        " (default is current directory)",
    )
    parser.add_argument(
        "--root",
        action="store_true",
        help="Use UID 0 and GID 0 (i.e., fake root account) within container. "
        "This is mostly safe, but processes can use this to circumvent some file system"
        " restrictions of the container and access otherwise hidden directories.",
    )
    parser.add_argument(
        "--uid",
        metavar="UID",
        type=int,
        default=None,
        help="use given UID within container (default: current UID)",
    )
    parser.add_argument(
        "--gid",
        metavar="GID",
        type=int,
        default=None,
        help="use given GID within container (default: current UID)",
    )
    parser.add_argument(
        "--cgroup-access",
        action="store_true",
        help="Allow processes in the container to use cgroups. "
        "This only works on cgroupsv2 systems and if containerexec is either started in"
        " its own cgroup or can talk to systemd to create a cgroup (same requirements"
        " as for runexec).",
    )
    add_basic_container_args(parser)
    add_container_output_args(parser)
    baseexecutor.add_basic_executor_options(parser)

    options = parser.parse_args(argv[1:])
    baseexecutor.handle_basic_executor_options(options)
    logging.debug("This is containerexec %s.", __version__)
    container_options = handle_basic_container_args(options, parser)
    container_options["cgroup_access"] = options.cgroup_access
    container_output_options = handle_container_output_args(options, parser)

    if options.root:
        if options.uid is not None or options.gid is not None:
            parser.error("Cannot combine option --root with --uid/--gid")
        options.uid = 0
        options.gid = 0

    logging.info("Starting command %s", shlex.join(options.args))

    executor = ContainerExecutor(uid=options.uid, gid=options.gid, **container_options)

    # Ensure that process gets killed on interrupt/kill signal,
    # and avoid KeyboardInterrupt because it could occur anywhere.
    def signal_handler_kill(signum, frame):
        executor.stop()

    signal.signal(signal.SIGTERM, signal_handler_kill)
    signal.signal(signal.SIGQUIT, signal_handler_kill)
    signal.signal(signal.SIGINT, signal_handler_kill)

    # actual run execution
    try:
        result = executor.execute_run(
            options.args, workingDir=options.dir, **container_output_options
        )
    except (BenchExecException, OSError) as e:
        if options.debug:
            logging.exception(e)
        sys.exit(f"Cannot execute {shlex.quote(options.args[0])}: {e}.")
    return result.signal or result.value


class ContainerExecutor(baseexecutor.BaseExecutor):
    """Extended executor that allows to start the processes inside containers
    using Linux namespaces."""

    def __init__(
        self,
        use_namespaces=True,
        uid=None,
        gid=None,
        network_access=False,
        dir_modes={"/": DIR_OVERLAY, "/run": DIR_HIDDEN, "/tmp": DIR_HIDDEN},
        container_system_config=True,
        container_tmpfs=True,
        cgroup_access=False,
        *args,
        **kwargs,
    ):
        """Create instance.
        @param use_namespaces: If False, disable all container features of this class
            and ignore all other parameters.
        @param uid: Which UID to use inside container.
        @param gid: Which GID to use inside container.
        @param network_access:
            Whether to allow processes in the contain to access the network.
        @param dir_modes: Dict that specifies which directories should be accessible
            and how in the container.
        @param container_system_config: Whether to use a special system configuration in
            the container that disables all remote host and user lookups, sets a custom
            hostname, etc.
        @param cgroup_access:
            Whether to allow processes in the contain to access cgroups.
            Only supported on systems with cgroupsv2.
        """
        super(ContainerExecutor, self).__init__(*args, **kwargs)
        self._use_namespaces = use_namespaces
        if not use_namespaces:
            return
        self._container_tmpfs = container_tmpfs
        self._container_system_config = container_system_config
        self._uid = (
            uid
            if uid is not None
            else container.CONTAINER_UID if container_system_config else os.getuid()
        )
        self._gid = (
            gid
            if gid is not None
            else container.CONTAINER_GID if container_system_config else os.getgid()
        )
        self._allow_network = network_access
        self._env_override = {}

        if container_system_config:
            self._env_override["HOME"] = container.CONTAINER_HOME
            if container.CONTAINER_HOME not in dir_modes:
                dir_modes[container.CONTAINER_HOME] = DIR_HIDDEN

        if "/" not in dir_modes:
            raise ValueError("Need directory mode for '/'.")
        for path, kind in dir_modes.items():
            if kind not in DIR_MODES:
                raise ValueError(f"Invalid value '{kind}' for directory '{path}'.")
            if not os.path.isabs(path):
                raise ValueError(f"Invalid non-absolute directory '{path}'.")
            if path == "/proc":
                raise ValueError("Cannot specify directory mode for /proc.")
        # All dir_modes in dir_modes are sorted by length
        # to ensure parent directories come before child directories
        # All directories are bytes to avoid issues if existing mountpoints are invalid
        # UTF-8.
        sorted_special_dirs = sorted(
            ((path.encode(), kind) for (path, kind) in dir_modes.items()),
            key=lambda tupl: len(tupl[0]),
        )
        self._dir_modes = collections.OrderedDict(sorted_special_dirs)

        def is_accessible(path):
            mode = container.determine_directory_mode(self._dir_modes, path)
            return os.access(path, os.R_OK) and mode not in [None, container.DIR_HIDDEN]

        # Warn if LXCFS is not installed. This does not warn if LXCFS is hidden in the
        # container, but we do not want a warning per run.
        if not is_accessible(container.LXCFS_PROC_DIR):
            logging.info(
                "LXCFS is not available, some host information like the uptime"
                " and the total number of CPU cores leaks into the container."
            )

        if not NATIVE_CLONE_CALLBACK_SUPPORTED:
            logging.debug(
                "Using a non-robust fallback for clone callback. If you have many "
                "threads please read https://github.com/sosy-lab/benchexec/issues/435"
            )

        self._cgroups = Cgroups.dummy()
        if cgroup_access:
            self._cgroups = Cgroups.initialize(allowed_versions=[2])
            if self._cgroups.version != 2:
                sys.exit(
                    "Cgroup access unsupported on this system, "
                    "BenchExec only supports this for cgroupsv2."
                )
            if self._cgroups.CPU not in self._cgroups:
                self._cgroups.handle_errors([self._cgroups.CPU])

    def _get_result_files_base(self, temp_dir):
        """Given the temp directory that is created for each run, return the path to the
        directory where files created by the tool are stored."""
        if not self._use_namespaces:
            return super(ContainerExecutor, self)._get_result_files_base(temp_dir)
        else:
            return os.path.join(temp_dir, "temp")

    # --- run execution ---

    def execute_run(
        self,
        args,
        workingDir=None,  # noqa: N803 backwards-compatibility
        output_dir=None,
        result_files_patterns=[],
        rootDir=None,
        environ=None,
    ):
        """
        This method executes the command line and waits for the termination of it,
        handling all setup and cleanup.

        Note that this method does not expect to be interrupted by KeyboardInterrupt
        and does not guarantee proper cleanup if KeyboardInterrupt is raised!
        If this method runs on the main thread of your program,
        make sure to set a signal handler for signal.SIGINT that calls stop() instead.

        @param args: the command line to run
        @param rootDir: None or a root directory that contains all relevant files
            for starting a new process
        @param workingDir:
            None or a directory which the execution should use as working directory
        @param output_dir: the directory where to write result files
            (required if result_files_pattern)
        @param result_files_patterns:
            a list of patterns of files to retrieve as result files
        """
        # preparations
        temp_dir = None
        if rootDir is None:
            temp_dir = tempfile.mkdtemp(prefix="BenchExec_run_")
        if environ is None:
            environ = os.environ.copy()

        cgroups = self._cgroups.create_fresh_child_cgroup(
            self._cgroups.subsystems.keys()
        )
        tool_pid = None
        tool_cgroups = None
        returnvalue = 0

        logging.debug("Starting process.")

        try:
            tool_pid, tool_cgroups, result_fn = self._start_execution(
                args=args,
                stdin=None,
                stdout=None,
                stderr=None,
                env=environ,
                root_dir=rootDir,
                cwd=workingDir,
                temp_dir=temp_dir,
                cgroups=cgroups,
                output_dir=output_dir,
                result_files_patterns=result_files_patterns,
                child_setup_fn=util.dummy_fn,
                parent_setup_fn=util.dummy_fn,
                parent_cleanup_fn=util.dummy_fn,
            )

            with self.SUB_PROCESS_PIDS_LOCK:
                self.SUB_PROCESS_PIDS.add(tool_pid)

            # wait until process has terminated
            returnvalue, unused_ru_child, unused = result_fn()

        finally:
            # cleanup steps that need to get executed even in case of failure
            logging.debug("Process terminated, exit code %s.", returnvalue)

            with self.SUB_PROCESS_PIDS_LOCK:
                self.SUB_PROCESS_PIDS.discard(tool_pid)

            if temp_dir is not None:
                logging.debug("Cleaning up temporary directory.")
                util.rmtree(temp_dir, onerror=util.log_rmtree_error)

        # cleanup steps that are only relevant in case of success
        return util.ProcessExitCode.from_raw(returnvalue)

    def _start_execution(
        self,
        root_dir=None,
        output_dir=None,
        result_files_patterns=[],
        memlimit=None,
        memory_nodes=None,
        *args,
        **kwargs,
    ):
        if not self._use_namespaces:
            return super(ContainerExecutor, self)._start_execution(*args, **kwargs)
        else:
            if result_files_patterns:
                if not output_dir:
                    raise ValueError(
                        "Output directory needed for retaining result files."
                    )
                for pattern in result_files_patterns:
                    if not pattern:
                        raise ValueError(
                            f"Invalid empty result-files pattern "
                            f"in {result_files_patterns}"
                        )

                    pattern = os.path.normpath(pattern)
                    if pattern.startswith(".."):
                        raise ValueError(
                            f"Invalid relative result-files pattern '{pattern}'."
                        )

            while True:
                result = self._start_execution_in_container(
                    root_dir=root_dir,
                    output_dir=output_dir,
                    memlimit=memlimit,
                    memory_nodes=memory_nodes,
                    result_files_patterns=result_files_patterns,
                    *args,
                    **kwargs,
                )
                if result is not None:
                    return result
                # else retry as workaround for #656

    # --- container implementation with namespaces ---

    def _start_execution_in_container(
        self,
        args,
        stdin,
        stdout,
        stderr,
        env,
        root_dir,
        cwd,
        temp_dir,
        memlimit,
        memory_nodes,
        cgroups,
        output_dir,
        result_files_patterns,
        parent_setup_fn,
        child_setup_fn,
        parent_cleanup_fn,
    ):
        """Execute the given command and measure its resource usage similarly to
        super()._start_execution(), but inside a container implemented using Linux
        namespaces.  The command has no network access (only loopback),
        a fresh directory as /tmp and no write access outside of this,
        and it does not see other processes except itself.
        """
        assert self._use_namespaces

        if root_dir is None:
            env.update(self._env_override)

        # We have three processes involved:
        # parent: the current Python process in which RunExecutor is executing
        # child: child process in new namespace (PID 1 in inner namespace),
        #        configures inner namespace, serves as dummy init,
        #        collects result of grandchild and passes it to parent
        # grandchild: child of child process (PID 2 in inner namespace), exec()s tool

        # We need the following communication steps between these proceses:
        # 1a) grandchild tells parent its PID (in outer namespace).
        # 1b) grandchild tells parent that it is ready and measurement should begin.
        # 2) parent tells grandchild that measurement has begun and tool should
        #    be exec()ed.
        # 3) child tells parent about return value and resource consumption of
        #    grandchild.
        # 1a and 1b are done together by sending the PID through a pipe.
        # 2 is done by sending a null byte through a pipe.
        # 3 is done by sending a pickled object through the same pipe as #2.
        # We cannot use the same pipe for both directions, because otherwise a sender
        # might read the bytes it has sent itself.

        # Error codes from child to parent
        CHILD_OSERROR = 128  # noqa: N806 local constant
        CHILD_UNKNOWN_ERROR = 129  # noqa: N806 local constant

        # "downstream" pipe parent->grandchild
        from_parent, to_grandchild = os.pipe()
        # "upstream" pipe grandchild/child->parent
        from_grandchild, to_parent = os.pipe()

        # The protocol for these pipes is that first the parent sends the marker for
        # user mappings, then the grand child sends its outer PID back,
        # and finally the parent sends its completion marker.
        # After the run, the child sends the result of the grand child and then waits
        # for the post_run marker, before it terminates.
        MARKER_USER_MAPPING_COMPLETED = b"A"  # noqa: N806 local constant
        MARKER_PARENT_COMPLETED = b"B"  # noqa: N806 local constant
        MARKER_PARENT_POST_RUN_COMPLETED = b"C"  # noqa: N806 local constant

        # If the current directory is within one of the bind mounts we create,
        # we need to cd into this directory again, otherwise we would not see the
        # bind mount, but the directory behind it.
        # Thus we always set cwd to force a change of directory.
        if root_dir is None:
            cwd = os.path.abspath(cwd or os.curdir)
        else:
            root_dir = os.path.abspath(root_dir)
            cwd = os.path.abspath(cwd)

        use_cgroup_ns = cgroups.version == 2

        def grandchild():
            """Setup everything inside the process that finally exec()s the tool."""
            try:
                # We know that this process has PID 2 in the inner namespace,
                # but we actually need to know its PID in the outer namespace
                # such that parent can put us into the correct cgroups.  According to
                # http://man7.org/linux/man-pages/man7/pid_namespaces.7.html,
                # there are two ways to achieve this: sending a message with the PID
                # via a socket (but Python 2 lacks a convenient API for sendmsg),
                # and reading /proc/self in the outer procfs instance
                # (that's what we do).
                my_outer_pid = container.get_my_pid_from_procfs()

                container.mount_proc(self._container_system_config)
                container.reset_signal_handling()
                child_setup_fn()  # Do some other setup the caller wants.

                # Signal readiness to parent by sending our PID
                # and wait until parent is also ready
                os.write(to_parent, str(my_outer_pid).encode())
                received = os.read(from_parent, 1)
                assert received == MARKER_PARENT_COMPLETED, received

                # Finalize setup
                # We want to do as little as possible here because measurements are
                # already running, but we can only setup the cgroup namespace
                # once we are in the desired cgroup.
                if use_cgroup_ns:
                    container.setup_cgroup_namespace()
                container.drop_capabilities()
            except BaseException as e:
                # When using runexec, this logging will end up in the output.log file,
                # where usually the tool output is. This is suboptimal, but probably
                # better than swallowing it. (In cases where this logs something,
                # there will be no tool output, so at least no confusion.)
                # For a complete solution we would have to send the exception via
                # the to_parent pipe.
                logging.error(
                    "Error during final preparation of container in target process: %s",
                    e,
                )
                raise
            finally:
                # close remaining ends of pipe
                os.close(from_parent)
                os.close(to_parent)
            # here Python will exec() the tool for us

        def child():
            """Setup everything inside the container,
            start the tool, and wait for result."""
            try:
                logging.debug(
                    "Child: child process of RunExecutor with PID %d started",
                    container.get_my_pid_from_procfs(),
                )

                # Put all received signals on hold until we handle them later.
                container.block_all_signals()

                # We want to avoid leaking file descriptors to the executed child.
                # It is also nice if the child has only the minimal necessary file
                # descriptors, to avoid keeping other pipes and files open, e.g.,
                # those that the parent uses to communicate with other containers
                # (if containers are started in parallel).
                # Thus we do not use the close_fds feature of subprocess.Popen,
                # but do the same here manually. We keep the relevant ends of our pipes,
                # and stdin/out/err of child and grandchild.
                necessary_fds = {
                    sys.stdin,
                    sys.stdout,
                    sys.stderr,
                    to_parent,
                    from_parent,
                    stdin,
                    stdout,
                    stderr,
                } - {None}
                container.close_open_fds(keep_files=necessary_fds)

                try:
                    if self._container_system_config:
                        # A standard hostname increases reproducibility.
                        try:
                            socket.sethostname(container.CONTAINER_HOSTNAME)
                        except PermissionError:
                            logging.warning(
                                "Changing hostname in container prevented "
                                "by system configuration, "
                                "real hostname will leak into the container."
                            )

                    if not self._allow_network:
                        container.activate_network_interface("lo")

                    # Wait until user mapping is finished,
                    # this is necessary for filesystem writes
                    received = os.read(from_parent, len(MARKER_USER_MAPPING_COMPLETED))
                    assert received == MARKER_USER_MAPPING_COMPLETED, received

                    if root_dir is not None:
                        self._setup_root_filesystem(root_dir)
                    else:
                        self._setup_container_filesystem(
                            temp_dir,
                            output_dir if result_files_patterns else None,
                            memlimit,
                            memory_nodes,
                        )

                    # Marking this process as "non-dumpable" (no core dumps) also
                    # forbids several other ways how other processes can access and
                    # influence it:
                    # ptrace is forbidden and much of /proc/<child>/ is inaccessible.
                    # We set this to prevent the benchmarked tool from messing with this
                    # process or using it to escape from the container. More info:
                    # http://man7.org/linux/man-pages/man5/proc.5.html
                    # It needs to be done after MARKER_USER_MAPPING_COMPLETED.
                    libc.prctl(libc.PR_SET_DUMPABLE, libc.SUID_DUMP_DISABLE, 0, 0, 0)
                except OSError as e:
                    logging.critical(
                        "Failed to configure container with operation '%s': %s",
                        # Show executed statement, often the error does not contain
                        # information about what was attempted.
                        traceback.extract_tb(e.__traceback__, limit=-1)[0].line,
                        e,
                    )
                    if container.check_apparmor_userns_restriction(e):
                        logging.critical(container._ERROR_MSG_USER_NS_RESTRICTION)
                    return CHILD_OSERROR

                try:
                    os.chdir(cwd)
                except OSError as e:
                    logging.critical(
                        "Cannot change into working directory inside container: %s", e
                    )
                    return CHILD_OSERROR

                container.setup_seccomp_filter()

                try:
                    grandchild_proc = subprocess.Popen(
                        args,
                        stdin=stdin,
                        stdout=stdout,
                        stderr=stderr,
                        env=env,
                        close_fds=False,
                        preexec_fn=grandchild,
                    )
                except (OSError, RuntimeError) as e:
                    logging.critical("Cannot start process: %s", e)
                    return CHILD_OSERROR

                # keep capability for unmount if necessary later
                necessary_capabilities = (
                    [libc.CAP_SYS_ADMIN] if result_files_patterns else []
                )
                container.drop_capabilities(keep=necessary_capabilities)

                # Close other fds that were still necessary above.
                container.close_open_fds(
                    keep_files={sys.stdout, sys.stderr, to_parent, from_parent}
                )

                # Set up signal handlers to forward signals to grandchild
                # (because we are PID 1, there is a special signal handling otherwise).
                # cf. dumb-init project: https://github.com/Yelp/dumb-init
                # Also wait for grandchild and return its result.
                grandchild_result = container.wait_for_child_and_forward_signals(
                    grandchild_proc.pid, args[0]
                )

                logging.debug(
                    "Child: process %s terminated with exit code %d.",
                    args[0],
                    grandchild_result[0],
                )

                if result_files_patterns:
                    # Remove the bind mount that _setup_container_filesystem added
                    # such that the parent can access the result files.
                    libc.umount(temp_dir.encode())

                # Re-allow access to /proc/<child>/...,
                # this is used by the parent for accessing output files
                libc.prctl(libc.PR_SET_DUMPABLE, libc.SUID_DUMP_USER, 0, 0, 0)

                try:
                    os.write(to_parent, pickle.dumps(grandchild_result))
                except BrokenPipeError:
                    # Happens e.g. in nested BenchExec executions if parent is killed
                    # before child. If parent is killed, nothing matters anymore.
                    logging.debug("Broken pipe to parent, already terminated?")
                    os.close(to_parent)
                    os.close(from_parent)
                    return 0
                os.close(to_parent)

                # Now the parent copies the output files, we need to wait until this is
                # finished. If the child terminates, the container file system and its
                # tmpfs go away.
                received = os.read(from_parent, 1)
                assert received == MARKER_PARENT_POST_RUN_COMPLETED, received
                os.close(from_parent)

                return 0
            except OSError:
                logging.exception("Error in child process of RunExecutor")
                return CHILD_OSERROR
            except subprocess.SubprocessError as e:
                # only reason should be "Exception occurred in preexec_fn"
                if "Exception occurred in preexec_fn" in str(e):
                    logging.error(
                        "Error during final preparation of container in target process,"
                        " check logs."
                    )
                else:
                    logging.exception("Error in child process of RunExecutor")
                return CHILD_UNKNOWN_ERROR
            except BaseException:
                # Need to catch everything because this method always needs to return an
                # int (we are inside a C callback that requires returning int).
                logging.exception("Error in child process of RunExecutor")
                return CHILD_UNKNOWN_ERROR

        try:  # parent
            try:
                child_pid = container.execute_in_namespace(
                    child, use_network_ns=not self._allow_network
                )
            except OSError as e:
                if (
                    e.errno == errno.EPERM
                    and util.try_read_file("/proc/sys/kernel/unprivileged_userns_clone")
                    == "0"
                ):
                    raise BenchExecException(
                        "Unprivileged user namespaces forbidden on this system, please "
                        "enable them with 'sysctl -w kernel.unprivileged_userns_clone=1' "
                        "or disable container mode"
                    )
                elif (
                    e.errno in {errno.ENOSPC, errno.EINVAL}
                    and util.try_read_file("/proc/sys/user/max_user_namespaces") == "0"
                ):
                    # Ubuntu has ENOSPC, Centos seems to produce EINVAL in this case
                    raise BenchExecException(
                        "Unprivileged user namespaces forbidden on this system, please "
                        "enable by using 'sysctl -w user.max_user_namespaces=10000' "
                        "(or another value) or disable container mode"
                    )
                else:
                    raise BenchExecException(
                        "Creating namespace for container mode failed: "
                        + os.strerror(e.errno)
                    )
            logging.debug(
                "Parent: child process of RunExecutor with PID %d started.", child_pid
            )

            def check_child_exit_code():
                """Check if the child process terminated cleanly
                and raise an error otherwise."""
                child_exitcode, unused_child_rusage = self._wait_for_process(
                    child_pid, args[0]
                )
                child_exitcode = util.ProcessExitCode.from_raw(child_exitcode)
                logging.debug(
                    "Parent: child process of RunExecutor with PID %d"
                    " terminated with %s.",
                    child_pid,
                    child_exitcode,
                )

                if child_exitcode:
                    if child_exitcode.value:
                        if child_exitcode.value == CHILD_OSERROR:
                            # This was an OSError in the child,
                            # details were already logged
                            raise BenchExecException(
                                "execution in container failed, check log for details"
                            )
                        elif child_exitcode.value == CHILD_UNKNOWN_ERROR:
                            raise BenchExecException("unexpected error in container")
                        raise OSError(
                            child_exitcode.value, os.strerror(child_exitcode.value)
                        )
                    raise OSError(
                        0,
                        f"Child process of RunExecutor terminated with {child_exitcode}",
                    )

            # Close unnecessary ends of pipes such that read() does not block forever
            # if all other processes have terminated.
            os.close(from_parent)
            os.close(to_parent)

            container.setup_user_mapping(child_pid, uid=self._uid, gid=self._gid)
            # signal child to continue
            os.write(to_grandchild, MARKER_USER_MAPPING_COMPLETED)

            try:
                # Wait with timeout until from_grandchild becomes ready to be read.
                rlist, _, _ = select.select([from_grandchild], [], [], 60)
                if from_grandchild not in rlist:
                    # Timeout has occurred, likely deadlock in child (cf. #656).
                    logging.warning(
                        "Child %s not ready after 60s, likely "
                        "https://github.com/sosy-lab/benchexec/issues/656 occurred. "
                        "Killing it and trying again.",
                        child_pid,
                    )
                    # As long as we have not sent MARKER_PARENT_COMPLETED, the tool is
                    # not yet started and it is safe to kill the child and restart.
                    # Killing child (PID 1 in container) will also kill grandchild if it
                    # already exists.
                    util.kill_process(child_pid)
                    # Open pipes will be close in finally.
                    # Signal retry to caller.
                    return None

                # read at most 10 bytes because this is enough for 32bit int
                grandchild_pid = int(os.read(from_grandchild, 10))
            except ValueError:
                # probably empty read, i.e., pipe closed,
                # i.e., child or grandchild failed
                check_child_exit_code()
                assert False, (
                    "Child process of RunExecutor terminated cleanly"
                    " but did not send expected data."
                )

            logging.debug(
                "Parent: executing %s in grand child with PID %d"
                " via child with PID %d.",
                args[0],
                grandchild_pid,
                child_pid,
            )

            # cgroups is the cgroup where we configure limits.
            # We add another layer of cgroups below it, for two reasons:
            # - We want to move our child process (the init process of the container)
            #   into a cgroups where the limits apply because LXCFS reports the limits
            #   of the init process of the container.
            #   This has the disadvantage that in principle the memory limit also
            #   includes and applies to our child process, but there is no other way
            #   to make LXCFS report the limits correctly. And at least we do not
            #   include our child process in the measurements.
            # - On cgroupsv2 we want to move the grandchild process (the started tool)
            #   into a cgroup that becomes the root of the cgroup ns,
            #   such that no other cgroup (in particular the one with the limits)
            #   is accessible in the container and the limits cannot be changed
            #   from within the container.
            child_cgroup = cgroups.create_fresh_child_cgroup(
                cgroups.subsystems.keys(), prefix="init_"
            )
            child_cgroup.add_task(child_pid)
            grandchild_cgroups = cgroups.create_fresh_child_cgroup_for_delegation()

            # start measurements
            grandchild_cgroups.add_task(grandchild_pid)
            parent_setup = parent_setup_fn()

            # Signal grandchild that setup is finished
            os.write(to_grandchild, MARKER_PARENT_COMPLETED)

            # Copy file descriptor, otherwise we could not close from_grandchild in
            # finally block and would leak a file descriptor in case of exception.
            from_grandchild_copy = os.dup(from_grandchild)
            to_grandchild_copy = os.dup(to_grandchild)
        finally:
            os.close(from_grandchild)
            os.close(to_grandchild)

        def wait_for_grandchild():
            # 1024 bytes ought to be enough for everyone^Wour pickled result
            try:
                received = os.read(from_grandchild_copy, 1024)
            except OSError as e:
                if self.PROCESS_KILLED and e.errno == errno.EINTR:
                    # Read was interrupted because of Ctrl+C, we just try again
                    received = os.read(from_grandchild_copy, 1024)
                else:
                    raise e

            if not received:
                # Typically this means the child exited prematurely because an error
                # occurred, and check_child_exitcode() will handle this.
                # We close the pipe first, otherwise child could hang infinitely.
                os.close(from_grandchild_copy)
                os.close(to_grandchild_copy)
                check_child_exit_code()
                assert False, "Child process terminated cleanly without sending result"

            exitcode, ru_child = pickle.loads(received)

            base_path = f"/proc/{child_pid}/root"
            parent_cleanup = parent_cleanup_fn(
                parent_setup,
                util.ProcessExitCode.from_raw(exitcode),
                base_path,
                grandchild_cgroups,
            )

            if result_files_patterns:
                # As long as the child process exists
                # we can access the container file system here
                self._transfer_output_files(
                    base_path + temp_dir, cwd, output_dir, result_files_patterns
                )

            os.close(from_grandchild_copy)
            os.write(to_grandchild_copy, MARKER_PARENT_POST_RUN_COMPLETED)
            os.close(to_grandchild_copy)  # signal child that it can terminate
            check_child_exit_code()

            return exitcode, ru_child, parent_cleanup

        return grandchild_pid, grandchild_cgroups, wait_for_grandchild

    def _setup_container_filesystem(self, temp_dir, output_dir, memlimit, memory_nodes):
        """Setup the filesystem layout in the container.
        As first step, we create a copy of all existing mountpoints in mount_base,
        recursively, and as "private" mounts
        (i.e., changes to existing mountpoints afterwards won't propagate to our copy).
        Then we iterate over all mountpoints and change them according to the mode
        the user has specified (hidden, read-only, overlay, or full-access).
        This has do be done for each mountpoint because overlays are not recursive.
        Then we chroot into the new mount hierarchy.

        The new filesystem layout still has a view of the host's /proc. We do not mount
        a fresh /proc here because the grandchild still needs the old /proc.

        We do simply iterate over all existing mount points and set them to
        read-only/overlay them, because it is easier to create a new hierarchy and
        chroot into it. First, we still have access to the original mountpoints while
        doing so, and second, we avoid race conditions if someone else changes the
        existing mountpoints.

        @param temp_dir:
            The base directory under which all our directories should be created.
        """
        # All strings here are bytes to avoid issues
        # if existing mountpoints are invalid UTF-8.

        # directory with files created by tool
        temp_base = self._get_result_files_base(temp_dir).encode()
        temp_dir = temp_dir.encode()

        tmpfs_opts = [f"size={memlimit or '100%'}"]
        if memory_nodes:
            tmpfs_opts.append("mpol=bind:" + ",".join(map(str, memory_nodes)))
        tmpfs_opts = (",".join(tmpfs_opts)).encode()
        if self._container_tmpfs:
            libc.mount(None, temp_dir, b"tmpfs", 0, tmpfs_opts)

        mount_base = os.path.join(temp_dir, b"mount")  # base dir for container mounts
        os.mkdir(mount_base)
        os.mkdir(temp_base)

        # Overlayfs needs its own additional temporary directory ("work" directory).
        # temp_base will be the "upper" layer, the host FS the "lower" layer,
        # and mount_base the mount target.
        work_base = os.path.join(temp_dir, b"overlayfs")
        os.mkdir(work_base)

        # Copy all mounts to mount_base and apply directory modes
        container.duplicate_mount_hierarchy(
            mount_base, temp_base, work_base, self._dir_modes
        )

        # Now configure some special hard-coded cases

        def make_tmpfs_dir(path):
            """Ensure that a tmpfs is mounted on path, if the path exists"""
            if path in self._dir_modes:
                return  # explicitly configured by user
            mount_tmpfs = mount_base + path
            temp_tmpfs = temp_base + path
            os.makedirs(temp_tmpfs, exist_ok=True)
            if os.path.isdir(mount_tmpfs):
                # If we already have a tmpfs, we can just bind mount it,
                # otherwise we need one
                if self._container_tmpfs:
                    container.make_bind_mount(temp_tmpfs, mount_tmpfs)
                else:
                    libc.mount(None, mount_tmpfs, b"tmpfs", 0, tmpfs_opts)

        # The following directories should be writable RAM disks
        # for Posix shared memory. For example, the Python multiprocessing module
        # explicitly checks for a tmpfs instance.
        make_tmpfs_dir(b"/dev/shm")
        make_tmpfs_dir(b"/run/shm")

        if self._container_system_config:
            container.setup_container_system_config(
                temp_base, mount_base, self._dir_modes
            )

        if output_dir:
            # We need a way to see temp_base in the container in order to be able to
            # copy result files out of it, so we need a directory that is guaranteed to
            # exist in order to use it as mountpoint for a bind mount to temp_base.
            # Of course, the tool inside the container should not have access to
            # temp_base, so we will add another bind mount with an empty directory on
            # top (equivalent to --hidden-dir). After the tool terminates we can unmount
            # the top-level bind mount and then access temp_base. However, this works
            # only if there is no other mount point below that directory, and the user
            # can force us to create mount points at arbitrary directory if a directory
            # mode is specified. So we need an existing directory with no mount points
            # below, and luckily temp_dir fulfills all requirements (because we have
            # just created it as fresh drectory ourselves).
            # So we mount temp_base outside of the container to temp_dir inside.
            os.makedirs(mount_base + temp_dir, exist_ok=True)
            container.make_bind_mount(temp_base, mount_base + temp_dir, read_only=True)
            # And the following if branch will automatically hide the bind
            # mount below an empty directory.

        # If necessary, (i.e., if /tmp is not already hidden),
        # hide the directory where we store our files from processes in the container
        # by mounting an empty directory over it.
        if os.path.exists(mount_base + temp_dir):
            os.makedirs(temp_base + temp_dir, exist_ok=True)
            container.make_bind_mount(temp_base + temp_dir, mount_base + temp_dir)

        # Now we make mount_base the new root directory.
        container.chroot(mount_base)

    def _setup_root_filesystem(self, root_dir):
        """Setup the filesystem layout in the given root directory.
        Create a copy of the existing proc- and dev-mountpoints in the specified root
        directory. Afterwards we chroot into it.

        @param root_dir:
            The path of the root directory that is used to execute the process.
        """
        root_dir = root_dir.encode()

        # Create an empty proc folder into the root dir. The grandchild still needs a
        # view of the old /proc, therefore we do not mount a fresh /proc here.
        proc_base = os.path.join(root_dir, b"proc")
        os.makedirs(proc_base, exist_ok=True)

        dev_base = os.path.join(root_dir, b"dev")
        os.makedirs(dev_base, exist_ok=True)

        # Create a copy of the host's dev- and proc-mountpoints.
        # They are marked as private in order to not being changed
        # by existing mounts during run execution.
        container.make_bind_mount(b"/dev/", dev_base, recursive=True, private=True)
        container.make_bind_mount(b"/proc/", proc_base, recursive=True, private=True)

        os.chroot(root_dir)

    def _transfer_output_files(
        self, tool_output_dir, working_dir, output_dir, patterns
    ):
        """Transfer files created by the tool in the container to the output directory.
        @param tool_output_dir:
            The directory under which all tool output files are created.
        @param working_dir: The absolute working directory of the tool in the container.
        @param output_dir: the directory where to write result files
        @param patterns: a list of patterns of files to retrieve as result files
        """
        assert output_dir
        assert patterns
        if any(os.path.isabs(pattern) for pattern in patterns):
            base_dir = tool_output_dir
        else:
            base_dir = tool_output_dir + working_dir
        file_count = 0

        def transfer_file(abs_file):
            assert abs_file.startswith(base_dir)

            # We ignore (empty) directories, because we create them for hidden dirs etc.
            # We ignore device nodes, because overlayfs creates them.
            # We also ignore all other files (symlinks, fifos etc.),
            # because they are probably irrelevant, and just handle regular files.
            file = os.path.join("/", os.path.relpath(abs_file, base_dir))
            if (
                os.path.isfile(abs_file)
                and not os.path.islink(abs_file)
                and not container.is_container_system_config_file(file)
            ):
                target = output_dir + file

                nonlocal file_count
                file_count += 1
                if file_count <= _MAX_RESULT_FILE_LOG_COUNT:
                    logging.debug("Transferring output file %s to %s", abs_file, target)
                    if file_count == _MAX_RESULT_FILE_LOG_COUNT:
                        logging.debug(
                            "%s output files transferred, "
                            "further files will not be logged.",
                            file_count,
                        )

                os.makedirs(os.path.dirname(target), exist_ok=True)
                try:
                    # move is more efficient than copy in case both abs_file and target
                    # are on the same filesystem, and it avoids matching the file again
                    # with the next pattern.
                    shutil.move(abs_file, target)
                except OSError as e:
                    logging.warning("Could not retrieve output file '%s': %s", file, e)

        for pattern in patterns:
            if os.path.isabs(pattern):
                pattern = tool_output_dir + pattern
            else:
                pattern = tool_output_dir + os.path.join(working_dir, pattern)
            # normalize pattern for preventing directory traversal attacks:
            for abs_file in glob.iglob(os.path.normpath(pattern), recursive=True):
                # We allow the user to match directories and transfer them recursively.
                if os.path.isdir(abs_file):
                    for root, _unused_dirs, files in os.walk(abs_file):
                        for file in files:
                            transfer_file(os.path.join(root, file))
                else:
                    transfer_file(abs_file)

        logging.debug(
            "%s output files matched the patterns and were transferred.", file_count
        )


if __name__ == "__main__":
    main()
