# BenchExec is a framework for reliable benchmarking.
# This file is part of BenchExec.
#
# Copyright (C) 2007-2016  Dirk Beyer
# All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# prepare for Python 3
from __future__ import absolute_import, division, print_function, unicode_literals

# THIS MODULE HAS TO WORK WITH PYTHON 2.7!

import argparse
import errno
import logging
import os
import collections
import shutil
try:
    import cPickle as pickle
except ImportError:
    import pickle
import resource  # @UnusedImport necessary to eagerly import this module
import signal
import subprocess
import sys
import tempfile
sys.dont_write_bytecode = True # prevent creation of .pyc files

from benchexec import baseexecutor
from benchexec import BenchExecException
from benchexec.cgroups import Cgroup
from benchexec import container
from benchexec import libc
from benchexec import util

DIR_HIDDEN = "hidden"
DIR_READ_ONLY = "read-only"
DIR_OVERLAY = "overlay"
DIR_FULL_ACCESS = "full-access"
DIR_MODES = [DIR_HIDDEN, DIR_READ_ONLY, DIR_OVERLAY, DIR_FULL_ACCESS]


def add_basic_container_args(argument_parser):
    argument_parser.add_argument("--network-access", action="store_true",
        help="allow process to use network communication")
    argument_parser.add_argument("--keep-system-config",
        dest="container_system_config", action="store_false",
        help="do not use a special minimal configuration for local user and host lookups inside the container")
    argument_parser.add_argument("--keep-tmp", action="store_true",
        help="do not use a private /tmp for process (same as '--full-access-dir /tmp')")
    argument_parser.add_argument("--hidden-dir", metavar="DIR", action="append", default=[],
        help="hide this directory by mounting an empty directory over it "
            "(default for '/tmp' and '/run')")
    argument_parser.add_argument("--read-only-dir", metavar="DIR", action="append", default=[],
        help="make this directory visible read-only in the container")
    argument_parser.add_argument("--overlay-dir", metavar="DIR", action="append", default=[],
        help="mount an overlay filesystem over this directory "
            "that redirects all write accesses to temporary files (default for '/')")
    argument_parser.add_argument("--full-access-dir", metavar="DIR", action="append", default=[],
        help="give full access (read/write) to this host directory to processes inside container")

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
                "Cannot specify directory mode for '{}' because it does not exist or is no directory."
                .format(path))
        if path in dir_modes:
            error_fn("Cannot specify multiple directory modes for '{}'.".format(path))
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
    elif not "/tmp" in dir_modes:
        dir_modes["/tmp"] = DIR_HIDDEN

    if not "/" in dir_modes:
        dir_modes["/"] = DIR_OVERLAY
    if not "/run" in dir_modes:
        dir_modes["/run"] = DIR_HIDDEN

    if options.container_system_config:
        if dir_modes.get("/etc", dir_modes["/"]) != DIR_OVERLAY:
            logging.warning("Specified directory mode for /etc implies --keep-system-config, "
                "i.e., the container cannot be configured to force only local user and host lookups. "
                "Use --overlay-dir /etc to allow overwriting system configuration in the container.")
            options.container_system_config = False
        elif options.network_access:
            logging.warning("The container configuration disables DNS, "
                "host lookups will fail despite --network-access. "
                "Consider using --keep-system-config.")

    return {
        'network_access': options.network_access,
        'container_system_config': options.container_system_config,
        'dir_modes': dir_modes,
        }


def add_container_output_args(argument_parser):
    """Define command-line arguments for output of a container (result files).
    @param argument_parser: an argparse parser instance
    """
    argument_parser.add_argument("--output-directory", metavar="DIR", default="output.files",
        help="target directory for result files (default: './output.files')")
    argument_parser.add_argument("--result-files", metavar="PATTERN", action="append", default=[],
        help="pattern for specifying which result files should be copied to the output directory "
            "(default: '.')")

def handle_container_output_args(options, parser):
    """Handle the options specified by add_container_output_args().
    @return: a dict that can be used as kwargs for the ContainerExecutor.execute_run()
    """
    if options.result_files:
        result_files_patterns = [os.path.normpath(p) for p in options.result_files if p]
        for pattern in result_files_patterns:
            if pattern.startswith(".."):
                parser.error("Invalid relative result-files pattern '{}'.".format(pattern))
    else:
        result_files_patterns = ["."]

    output_dir = options.output_directory
    if os.path.exists(output_dir) and not os.path.isdir(output_dir):
        parser.error("Output directory '{}' must not refer to an existing file.".format(output_dir))
    return {
        'output_dir': output_dir,
        'result_files_patterns': result_files_patterns,
        }


def main(argv=None):
    """
    A simple command-line interface for the containerexecutor module of BenchExec.
    """
    if argv is None:
        argv = sys.argv

    # parse options
    parser = argparse.ArgumentParser(
        fromfile_prefix_chars='@',
        description=
        """Execute a command inside a simple container, i.e., partially isolated from the host.
           Command-line parameters can additionally be read from a file if file name prefixed with '@' is given as argument.
           Part of BenchExec: https://github.com/sosy-lab/benchexec/""")
    parser.add_argument("--dir", metavar="DIR",
                        help="working directory for executing the command (default is current directory)")
    parser.add_argument("--root", action="store_true",
                        help="use UID 0 and GID 0 (i.e., fake root account) within container")
    parser.add_argument("--uid", metavar="UID", type=int, default=None,
                        help="use given UID within container (default: current UID)")
    parser.add_argument("--gid", metavar="GID", type=int, default=None,
                        help="use given GID within container (default: current UID)")
    add_basic_container_args(parser)
    add_container_output_args(parser)
    baseexecutor.add_basic_executor_options(parser)

    options = parser.parse_args(argv[1:])
    baseexecutor.handle_basic_executor_options(options, parser)
    container_options = handle_basic_container_args(options, parser)
    container_output_options = handle_container_output_args(options, parser)

    if options.root:
        if options.uid is not None or options.gid is not None:
            parser.error("Cannot combine option --root with --uid/--gid")
        options.uid = 0
        options.gid = 0

    formatted_args = " ".join(map(util.escape_string_shell, options.args))
    logging.info('Starting command %s', formatted_args)

    executor = ContainerExecutor(uid=options.uid, gid=options.gid, **container_options)

    # ensure that process gets killed on interrupt/kill signal
    def signal_handler_kill(signum, frame):
        executor.stop()
    signal.signal(signal.SIGTERM, signal_handler_kill)
    signal.signal(signal.SIGINT,  signal_handler_kill)

    # actual run execution
    try:
        result = executor.execute_run(options.args, workingDir=options.dir,
                                      **container_output_options)
    except (BenchExecException, OSError) as e:
        if options.debug:
            logging.exception(e)
        sys.exit("Cannot execute {0}: {1}".format(util.escape_string_shell(options.args[0]), e))
    return result.signal or result.value

class ContainerExecutor(baseexecutor.BaseExecutor):
    """Extended executor that allows to start the processes inside containers
    using Linux namespaces."""

    def __init__(self, use_namespaces=True,
                 uid=None, gid=None,
                 network_access=False,
                 dir_modes={"/": DIR_OVERLAY, "/run": DIR_HIDDEN, "/tmp": DIR_HIDDEN},
                 container_system_config=True,
                 *args, **kwargs):
        """Create instance.
        @param use_namespaces: If False, disable all container features of this class
            and ignore all other parameters.
        @param uid: Which UID to use inside container.
        @param gid: Which GID to use inside container.
        @param network_access: Whether to allow processes in the contain to access the network.
        @param dir_modes: Dict that specifies which directories should be accessible and how in the container.
        @param container_system_config: Whether to use a special system configuration in the container
            that disables all remote host and user lookups.
        """
        super(ContainerExecutor, self).__init__(*args, **kwargs)
        self._use_namespaces = use_namespaces
        if not use_namespaces:
            return
        self._container_system_config = container_system_config
        self._uid = (uid if uid is not None
                     else container.CONTAINER_UID if container_system_config
                     else os.getuid())
        self._gid = (gid if gid is not None
                     else container.CONTAINER_GID if container_system_config
                     else os.getgid())
        self._allow_network = network_access
        self._env = None

        if container_system_config:
            if dir_modes.get("/etc", dir_modes.get("/")) != DIR_OVERLAY:
                raise ValueError("Cannot setup minimal system configuration for the container "
                    "without overlay filesystem for /etc.")
            self._env = os.environ.copy()
            self._env["HOME"] = container.CONTAINER_HOME
            if not container.CONTAINER_HOME in dir_modes:
                dir_modes[container.CONTAINER_HOME] = DIR_HIDDEN

        if not "/" in dir_modes:
            raise ValueError("Need directory mode for '/'.")
        for path, kind in dir_modes.items():
            if kind not in DIR_MODES:
                raise ValueError("Invalid value '{}' for directory '{}'.".format(kind, path))
            if not os.path.isabs(path):
                raise ValueError("Invalid non-absolute directory '{}'.".format(path))
            if path == "/proc":
                raise ValueError("Cannot specify directory mode for /proc.")
        # All dir_modes in dir_modes are sorted by length
        # to ensure parent directories come before child directories
        # All directories are bytes to avoid issues if existing mountpoints are invalid UTF-8.
        sorted_special_dirs = sorted(
            ((path.encode(), kind) for (path, kind) in dir_modes.items()),
            key=lambda tupl : len(tupl[0]))
        self._dir_modes = collections.OrderedDict(sorted_special_dirs)


    # --- run execution ---

    def execute_run(self, args, workingDir=None, output_dir=None, result_files_patterns=[]):
        """
        This method executes the command line and waits for the termination of it,
        handling all setup and cleanup.
        @param args: the command line to run
        @param workingDir: None or a directory which the execution should use as working directory
        @param output_dir: the directory where to write result files (required if result_files_pattern)
        @param result_files_patterns: a list of patterns of files to retrieve as result files
        """
        # preparations
        temp_dir = tempfile.mkdtemp(prefix="BenchExec_run_")

        pid = None
        returnvalue = 0

        logging.debug('Starting process.')

        try:
            pid, result_fn = self._start_execution(args=args,
                stdin=None, stdout=None, stderr=None,
                env=self._env, cwd=workingDir, temp_dir=temp_dir,
                cgroups=Cgroup({}),
                output_dir=output_dir, result_files_patterns=result_files_patterns,
                child_setup_fn=lambda: None,
                parent_setup_fn=lambda: None,
                parent_cleanup_fn=id)

            with self.SUB_PROCESS_PIDS_LOCK:
                self.SUB_PROCESS_PIDS.add(pid)

            returnvalue, unused_ru_child, unused = result_fn() # blocks until process has terminated

        finally:
            # cleanup steps that need to get executed even in case of failure
            logging.debug('Process terminated, exit code %s.', returnvalue)

            with self.SUB_PROCESS_PIDS_LOCK:
                self.SUB_PROCESS_PIDS.discard(pid)

            logging.debug('Cleaning up temporary directory.')
            util.rmtree(temp_dir, onerror=util.log_rmtree_error)

        # cleanup steps that are only relevant in case of success
        return util.ProcessExitCode.from_raw(returnvalue)

    def _start_execution(self, output_dir=None, result_files_patterns=[], *args, **kwargs):
        if not self._use_namespaces:
            return super(ContainerExecutor, self)._start_execution(*args, **kwargs)
        else:
            if result_files_patterns:
                if not output_dir:
                    raise ValueError("Output directory needed for retaining result files.")
                for pattern in result_files_patterns:
                    if not pattern:
                        raise ValueError("Invalid empty result-files pattern in {}"
                                         .format(result_files_patterns))

                    pattern = os.path.normpath(pattern)
                    if pattern.startswith(".."):
                        raise ValueError("Invalid relative result-files pattern '{}'."
                                         .format(pattern))

            return self._start_execution_in_container(
                output_dir=output_dir, result_files_patterns=result_files_patterns, *args, **kwargs)


    # --- container implementation with namespaces ---

    def _start_execution_in_container(
            self, args, stdin, stdout, stderr, env, cwd, temp_dir, cgroups,
            output_dir, result_files_patterns,
            parent_setup_fn, child_setup_fn, parent_cleanup_fn):
        """Execute the given command and measure its resource usage similarly to super()._start_execution(),
        but inside a container implemented using Linux namespaces.
        The command has no network access (only loopback),
        a fresh directory as /tmp and no write access outside of this,
        and it does not see other processes except itself.
        """
        assert self._use_namespaces

        args = self._build_cmdline(args, env=env)

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
        # 3) child tells parent about return value and resource consumption of grandchild.
        # 1a and 1b are done together by sending the PID through a pipe.
        # 2 is done by sending a null byte through a pipe.
        # 3 is done by sending a pickled object through the same pipe as #2.
        # We cannot use the same pipe for both directions, because otherwise a sender might
        # read the bytes it has sent itself.

        from_parent, to_grandchild = os.pipe() # "downstream" pipe parent->grandchild
        from_grandchild, to_parent = os.pipe() # "upstream" pipe grandchild/child->parent

        # If the current directory is within one of the bind mounts we create,
        # we need to cd into this directory again, otherwise we would not see the bind mount,
        # but the directory behind it. Thus we always set cwd to force a change of directory.
        cwd = os.path.abspath(cwd or os.curdir)

        def grandchild():
            """Setup everything inside the process that finally exec()s the tool."""
            try:
                # We know that this process has PID 2 in the inner namespace,
                # but we actually need to know its PID in the outer namespace
                # such that parent can put us into the correct cgroups.
                # According to http://man7.org/linux/man-pages/man7/pid_namespaces.7.html,
                # there are two ways to achieve this: sending a message with the PID
                # via a socket (but Python < 3.3 lacks a convenient API for sendmsg),
                # and reading /proc/self in the outer procfs instance (that's what we do).
                my_outer_pid = container.get_my_pid_from_procfs()

                container.mount_proc()
                container.drop_capabilities()
                child_setup_fn() # Do some other setup the caller wants.

                # Signal readiness to parent by sending our PID and wait until parent is also ready
                os.write(to_parent, str(my_outer_pid).encode())
                received = os.read(from_parent, 1)
                assert received == b'\0', received
            finally:
                # close remaining ends of pipe
                os.close(from_parent)
                os.close(to_parent)
            # here Python will exec() the tool for us

        def child():
            """Setup everything inside the container, start the tool, and wait for result."""
            try:
                logging.debug("Child: child process of RunExecutor with PID %d started",
                              container.get_my_pid_from_procfs())

                # We want to avoid leaking file descriptors to the executed child.
                # It is also nice if the child has only the minimal necessary file descriptors,
                # to avoid keeping other pipes and files open, e.g., those that the parent
                # uses to communicate with other containers (if containers are started in parallel).
                # Thus we do not use the close_fds feature of subprocess.Popen,
                # but do the same here manually.
                # We keep the relevant ends of our pipes, and stdin/out/err of child and grandchild.
                necessary_fds = {sys.stdin, sys.stdout, sys.stderr,
                    to_parent, from_parent, stdin, stdout, stderr} - {None}
                container.close_open_fds(keep_files=necessary_fds)

                try:
                    if not self._allow_network:
                        container.activate_network_interface("lo")
                    self._setup_container_filesystem(temp_dir)
                except EnvironmentError as e:
                    logging.critical("Failed to configure container: %s", e)
                    return int(e.errno)

                try:
                    os.chdir(cwd)
                except EnvironmentError as e:
                    logging.critical(
                        "Cannot change into working directory inside container: %s", e)
                    return int(e.errno)

                try:
                    grandchild_proc = subprocess.Popen(args,
                                        stdin=stdin,
                                        stdout=stdout, stderr=stderr,
                                        env=env,
                                        close_fds=False,
                                        preexec_fn=grandchild)
                except (EnvironmentError, RuntimeError) as e:
                    logging.critical("Cannot start process: %s", e)
                    try:
                        return int(e.errno)
                    except BaseException:
                        # subprocess.Popen in Python 2.7 throws OSError with errno=None
                        # if the preexec_fn fails.
                        return -2

                container.drop_capabilities()

                # Set up signal handlers to forward signals to grandchild
                # (because we are PID 1, there is a special signal handling otherwise).
                # cf. dumb-init project: https://github.com/Yelp/dumb-init
                container.forward_all_signals(grandchild_proc.pid, args[0])

                # Close other fds that were still necessary above.
                container.close_open_fds(keep_files={sys.stdout, sys.stderr, to_parent})

                # wait for grandchild and return its result
                grandchild_result = self._wait_for_process(grandchild_proc.pid, args[0])
                logging.debug("Child: process %s terminated with exit code %d.",
                              args[0], grandchild_result[0])
                os.write(to_parent, pickle.dumps(grandchild_result))
                os.close(to_parent)

                return 0
            except EnvironmentError as e:
                logging.exception("Error in child process of RunExecutor")
                return int(e.errno)
            except:
                # Need to catch everything because this method always needs to return a int
                # (we are inside a C callback that requires returning int).
                logging.exception("Error in child process of RunExecutor")
                return -1

        try: # parent
            try:
                child_pid = container.execute_in_namespace(child, use_network_ns=not self._allow_network)
            except OSError as e:
                raise BenchExecException(
                    "Creating namespace for container mode failed: " + os.strerror(e.errno))
            logging.debug("Parent: child process of RunExecutor with PID %d started.", child_pid)

            def check_child_exit_code():
                """Check if the child process terminated cleanly and raise an error otherwise."""
                child_exitcode, unused_child_rusage = self._wait_for_process(child_pid, args[0])
                child_exitcode = util.ProcessExitCode.from_raw(child_exitcode)
                logging.debug("Parent: child process of RunExecutor with PID %d terminated with %s.",
                              child_pid, child_exitcode)

                if child_exitcode:
                    if child_exitcode.value and child_exitcode.value <= 128:
                        # This was an OSError in the child, re-create it
                        raise OSError(child_exitcode.value, os.strerror(child_exitcode.value))
                    raise OSError(0, "Child process of RunExecutor terminated with " + str(child_exitcode))

            # Close unnecessary ends of pipes such that read() does not block forever
            # if all other processes have terminated.
            os.close(from_parent)
            os.close(to_parent)

            container.setup_user_mapping(child_pid, uid=self._uid, gid=self._gid)

            try:
                grandchild_pid = int(os.read(from_grandchild, 10)) # 10 bytes is enough for 32bit int
            except ValueError:
                # probably empty read, i.e., pipe closed, i.e., child or grandchild failed
                check_child_exit_code()
                assert False, "Child process of RunExecutor terminated cleanly but did not send expected data."

            logging.debug("Parent: executing %s in grand child with PID %d via child with PID %d.",
                          args[0], grandchild_pid, child_pid)

            # start measurements
            cgroups.add_task(grandchild_pid)
            parent_setup = parent_setup_fn()

            # Signal grandchild that setup is finished
            os.write(to_grandchild, b'\0')

            # Copy file descriptor, otherwise we could not close from_grandchild in finally block
            # and would leak a file descriptor in case of exception.
            from_grandchild_copy = os.dup(from_grandchild)
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

            parent_cleanup = parent_cleanup_fn(parent_setup)

            os.close(from_grandchild_copy)
            check_child_exit_code()

            if result_files_patterns:
                self._transfer_output_files(temp_dir, cwd, output_dir, result_files_patterns)

            exitcode, ru_child = pickle.loads(received)
            return exitcode, ru_child, parent_cleanup

        return grandchild_pid, wait_for_grandchild


    def _setup_container_filesystem(self, temp_dir):
        """Setup the filesystem layout in the container.
         As first step, we create a copy of all existing mountpoints in mount_base, recursively,
        and as "private" mounts (i.e., changes to existing mountpoints afterwards won't propagate
        to our copy).
        Then we iterate over all mountpoints and change them
        according to the mode the user has specified (hidden, read-only, overlay, or full-access).
        This has do be done for each mountpoint because overlays are not recursive.
        Then we chroot into the new mount hierarchy.

        The new filesystem layout still has a view of the host's /proc.
        We do not mount a fresh /proc here because the grandchild still needs old the /proc.

        We do simply iterate over all existing mount points and set them to read-only/overlay them,
        because it is easier create a new hierarchy and chroot into it.
        First, we still have access to the original mountpoints while doing so,
        and second, we avoid race conditions if someone else changes the existing mountpoints.

        @param temp_dir: The base directory under which all our directories should be created.
        """
        # All strings here are bytes to avoid issues if existing mountpoints are invalid UTF-8.
        temp_dir = temp_dir.encode()
        mount_base = os.path.join(temp_dir, b"mount") # base dir for container mounts
        temp_base = os.path.join(temp_dir, b"temp") # directory with files created by tool
        os.mkdir(mount_base)
        os.mkdir(temp_base)

        def _is_below(path, target_path):
            # compare with trailing slashes for cases like /foo and /foobar
            path = os.path.join(path, b"")
            target_path = os.path.join(target_path, b"")
            return path.startswith(target_path)

        def find_mode_for_dir(path, fstype):
            if (path == b"/proc"):
                # /proc is necessary for the grandchild to read PID, will be replaced later.
                return DIR_READ_ONLY
            if _is_below(path, b"/proc"):
                # Irrelevant.
                return None

            parent_mode = None
            result_mode = None
            for special_dir, mode in self._dir_modes.items():
                if _is_below(path, special_dir):
                    if path != special_dir:
                        parent_mode = mode
                    result_mode = mode
            assert result_mode is not None

            if result_mode == DIR_OVERLAY and (
                    _is_below(path, b"/dev") or
                    _is_below(path, b"/sys") or
                    fstype == b"autofs" or
                    fstype == b"cgroup"):
                # Import /dev, /sys, cgroup, and autofs from host into the container,
                # overlay does not work for them.
                return DIR_READ_ONLY

            if result_mode == DIR_HIDDEN and parent_mode == DIR_HIDDEN:
                # No need to recursively recreate mountpoints in hidden dirs.
                return None
            return result_mode

        # Overlayfs needs its own additional temporary directory ("work" directory).
        # temp_base will be the "upper" layer, the host FS the "lower" layer,
        # and mount_base the mount target.
        work_base = os.path.join(temp_dir, b"overlayfs")
        os.mkdir(work_base)

        if self._container_system_config:
            container.setup_container_system_config(temp_base)

        # Create a copy of host's mountpoints.
        container.make_bind_mount(b"/", mount_base, recursive=True, private=True)

        # Ensure each special dir is a mountpoint such that the next loop covers it.
        for special_dir in self._dir_modes.keys():
            mount_path = mount_base + special_dir
            temp_path = temp_base + special_dir
            try:
                container.make_bind_mount(mount_path, mount_path)
            except OSError as e:
                logging.debug("Failed to make %s a bind mount: %s", mount_path, e)
            if not os.path.exists(temp_path):
                os.makedirs(temp_path)

        # Set desired access mode for each mountpoint.
        for unused_source, full_mountpoint, fstype, options in list(container.get_mount_points()):
            if not _is_below(full_mountpoint, mount_base):
                continue
            mountpoint = full_mountpoint[len(mount_base):] or b"/"

            mount_path = mount_base + mountpoint
            temp_path = temp_base + mountpoint
            work_path = work_base + mountpoint

            mode = find_mode_for_dir(mountpoint, fstype)
            if mode == DIR_OVERLAY:
                if not os.path.exists(temp_path):
                    os.makedirs(temp_path)
                if not os.path.exists(work_path):
                    os.makedirs(work_path)
                try:
                    # Previous mount in this place not needed if replaced with overlay dir.
                    libc.umount(mount_path)
                except OSError as e:
                    logging.debug(e)
                try:
                    container.make_overlay_mount(mount_path, mountpoint, temp_path, work_path)
                except OSError as e:
                    raise OSError(e.errno,
                        "Creating overlay mount for '{}' failed: {}. "
                        "Please use other directory modes."
                            .format(mountpoint.decode(), os.strerror(e.errno)))

            elif mode == DIR_HIDDEN:
                if not os.path.exists(temp_path):
                    os.makedirs(temp_path)
                try:
                    # Previous mount in this place not needed if replaced with hidden dir.
                    libc.umount(mount_path)
                except OSError as e:
                    logging.debug(e)
                container.make_bind_mount(temp_path, mount_path)

            elif mode == DIR_READ_ONLY:
                try:
                    container.remount_with_additional_flags(mount_path, options, libc.MS_RDONLY)
                except OSError as e:
                    if e.errno == errno.EACCES:
                        logging.warning(
                            "Cannot mount '%s', directory may be missing from container.",
                            mountpoint.decode())
                    else:
                        # If this mountpoint is below an overlay/hidden dir re-create mountpoint.
                        # Linux does not support making read-only bind mounts in one step:
                        # https://lwn.net/Articles/281157/ http://man7.org/linux/man-pages/man8/mount.8.html
                        container.make_bind_mount(
                            mountpoint, mount_path, recursive=True, private=True)
                        container.remount_with_additional_flags(mount_path, options, libc.MS_RDONLY)

            elif mode == DIR_FULL_ACCESS:
                try:
                    # Ensure directory is still a mountpoint by attempting to remount.
                    container.remount_with_additional_flags(mount_path, options, 0)
                except OSError as e:
                    if e.errno == errno.EACCES:
                        logging.warning(
                            "Cannot mount '%s', directory may be missing from container.",
                            mountpoint.decode())
                    else:
                        # If this mountpoint is below an overlay/hidden dir re-create mountpoint.
                        container.make_bind_mount(
                            mountpoint, mount_path, recursive=True, private=True)

            elif mode is None:
                pass

            else:
                assert False

        # If necessary, (i.e., if /tmp is not already hidden),
        # hide the directory where we store our files from processes in the container
        # by mounting an empty directory over it.
        if os.path.exists(mount_base + temp_dir):
            os.makedirs(temp_base + temp_dir)
            container.make_bind_mount(temp_base + temp_dir, mount_base + temp_dir)

        os.chroot(mount_base)


    def _transfer_output_files(self, temp_dir, working_dir, output_dir, patterns):
        """Transfer files created by the tool in the container to the output directory.
        @param temp_dir: The base directory under which all our directories are created.
        @param working_dir: The absolute working directory of the tool in the container.
        @param output_dir: the directory where to write result files
        @param patterns: a list of patterns of files to retrieve as result files
        """
        assert output_dir and patterns
        tool_output_dir = os.path.join(temp_dir, "temp")
        if any(os.path.isabs(pattern) for pattern in patterns):
            base_dir = tool_output_dir
        else:
            base_dir = tool_output_dir + working_dir

        def transfer_file(abs_file):
            assert abs_file.startswith(base_dir)

            # We ignore (empty) directories, because we create them for hidden dirs etc.
            # We ignore device nodes, because overlayfs creates them.
            # We also ignore all other files (symlinks, fifos etc.),
            # because they are probably irrelevant, and just handle regular files.
            file = os.path.join("/", os.path.relpath(abs_file, base_dir))
            if (os.path.isfile(abs_file) and not os.path.islink(abs_file) and
                    not container.is_container_system_config_file(file)):
                target = output_dir + file
                try:
                    os.makedirs(os.path.dirname(target))
                except EnvironmentError:
                    pass # exist_ok=True not supported on Python 2
                try:
                    # move is more efficient than copy in case both abs_file and target
                    # are on the same filesystem, and it avoids matching the file again
                    # with the next pattern.
                    shutil.move(abs_file, target)
                except EnvironmentError as e:
                    logging.warning("Could not retrieve output file '%s': %s", file, e)

        for pattern in patterns:
            if os.path.isabs(pattern):
                pattern = tool_output_dir + pattern
            else:
                pattern = tool_output_dir + os.path.join(working_dir, pattern)
            # normalize pattern for preventing directory traversal attacks:
            for abs_file in util.maybe_recursive_iglob(os.path.normpath(pattern)):
                # Recursive matching is only supported starting with Python 3.5,
                # so we allow the user to match directories and transfer them recursively.
                if os.path.isdir(abs_file):
                    for root, unused_dirs, files in os.walk(abs_file):
                        for file in files:
                            transfer_file(os.path.join(root, file))
                else:
                    transfer_file(abs_file)


if __name__ == '__main__':
    main()
