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
try:
    import cPickle as pickle
except ImportError:
    import pickle
import resource  # @UnusedImport necessary to eagerly import this module
import signal
import subprocess
import sys
import tempfile
import threading
sys.dont_write_bytecode = True # prevent creation of .pyc files

from benchexec import baseexecutor
from benchexec.cgroups import Cgroup
from benchexec import container
from benchexec import libc
from benchexec import util

FS_OVERLAY = "overlay"
FS_READONLY = "read-only"
FS_MODES = [FS_OVERLAY, FS_READONLY]

DIR_HIDDEN = "hidden"
DIR_WRITABLE = "writable"


def add_basic_container_args(argument_parser):
    argument_parser.add_argument("--network-access", action="store_true",
        help="allow process to use network communication")
    argument_parser.add_argument("--keep-system-config",
        dest="container_system_config", action="store_false",
        help="do not use a special minimal configuration for local user and host lookups inside the container")
    argument_parser.add_argument("--file-system", metavar="MODE",
        choices=FS_MODES, default=FS_OVERLAY,
        help="how to organize the file-system layout: "
            "use an overlay file-system to isolate writes (default, 'overlay'), "
            "or make everything read-only ('read-only')")
    argument_parser.add_argument("--keep-tmp", action="store_true",
        help="do not use a private /tmp for process (same as '--writable-dir /tmp')")
    argument_parser.add_argument("--hide-dir", metavar="DIR", action="append", default=[],
        help="hide this directory by mounting an empty directory over it (default: /tmp)")
    argument_parser.add_argument("--writable-dir", metavar="DIR", action="append", default=[],
        help="let this directory be writable")

def handle_basic_container_args(options):
    """Handle the options specified by add_basic_container_args().
    @return: a dict that can be used as kwargs for the ContainerExecutor constructor
    """
    special_dirs = {}

    for path in options.writable_dir:
        path = os.path.abspath(path)
        if not os.path.isdir(path):
            sys.exit("Cannot make path '{}' writable because it does not exist or is no directory."
                     .format(path))
        special_dirs[path] = DIR_WRITABLE

    for path in options.hide_dir:
        path = os.path.abspath(path)
        if not os.path.isdir(path):
            sys.exit("Cannot hide path '{}' because it does not exist or is no directory."
                     .format(path))
        if path in special_dirs:
            sys.exit(
                "Cannot specify both --hide-dir and --writable-dir for directory {}.".format(path))
        special_dirs[path] = DIR_HIDDEN

    if options.keep_tmp:
        if "/tmp" in special_dirs and not special_dirs["/tmp"] == DIR_WRITABLE:
            sys.exit("Cannot specify both --keep-tmp and --hide-dir /tmp.")
        special_dirs["/tmp"] = DIR_WRITABLE
    elif not "/tmp" in special_dirs:
        special_dirs["/tmp"] = DIR_HIDDEN

    if options.container_system_config:
        if options.file_system != FS_OVERLAY:
            logging.warning("Option --file-system '%s' implies --keep-system-config, "
                "i.e., the container cannot be configured to force only local user and host lookups.",
                options.file_system)
            options.container_system_config = False
        elif options.network_access:
            logging.warning("The container configuration disables DNS, "
                "host lookups will fail despite --network-access. "
                "Consider using --keep-system-config.")

    return {
        'network_access': options.network_access,
        'container_system_config': options.container_system_config,
        'filesystem_mode': options.file_system,
        'special_dirs': special_dirs,
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
                        help="use UID 0 and GID 0 (i.e., fake root account) within namespace")
    parser.add_argument("--uid", metavar="UID", type=int, default=None,
                        help="use given UID within namespace (default: current UID)")
    parser.add_argument("--gid", metavar="GID", type=int, default=None,
                        help="use given GID within namespace (default: current UID)")
    add_basic_container_args(parser)
    baseexecutor.add_basic_executor_options(parser)

    options = parser.parse_args(argv[1:])
    baseexecutor.handle_basic_executor_options(options)
    container_options = handle_basic_container_args(options)

    if options.root:
        if options.uid is not None or options.gid is not None:
            sys.exit("Cannot combine option --root with --uid/--gid")
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
        result = executor.execute_run(options.args, workingDir=options.dir)
    except OSError as e:
        if options.debug:
            logging.exception(e)
        sys.exit("Cannot execute {0}: {1}".format(util.escape_string_shell(options.args[0]), e))
    return result.signal or result.value

class ContainerExecutor(baseexecutor.BaseExecutor):

    def __init__(self, use_namespaces=True,
                 uid=None, gid=None,
                 network_access=False,
                 filesystem_mode=FS_OVERLAY, special_dirs={},
                 container_system_config=True,
                 *args, **kwargs):
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
        if not filesystem_mode in FS_MODES:
            raise ValueError("Invalid filesystem mode '{}'.".format(filesystem_mode))
        self._filesystem_mode = filesystem_mode
        self._env = None
        if container_system_config:
            if filesystem_mode != FS_OVERLAY:
                raise ValueError("Cannot setup minimal system configuration for the container "
                    "without overlay filesystem.")
            self._env = os.environ.copy()
            self._env["HOME"] = container.CONTAINER_HOME

        for path, kind in special_dirs.items():
            if kind not in [DIR_HIDDEN, DIR_WRITABLE]:
                raise ValueError("Invalid value '{}' for directory '{}'.".format(kind, path))
            if not os.path.isabs(path):
                raise ValueError("Invalid non-absolute directory '{}'.".format(path))
            if not os.path.isdir(path):
                raise ValueError("Cannot handle dir '{}' specially if it does not exist.".format(path))
        if container_system_config and not container.CONTAINER_HOME in special_dirs:
            special_dirs[container.CONTAINER_HOME] = DIR_HIDDEN
        # All directories in special_dirs are sorted by length
        # to ensure parent directories come before child directories
        # All directories are bytes to avoid issues if existing mountpoints are invalid UTF-8.
        sorted_special_dirs = sorted(
            ((path.encode(), kind) for (path, kind) in special_dirs.items()),
            key=lambda tupl : len(tupl[0]))
        self._special_dirs = collections.OrderedDict(sorted_special_dirs)


    # --- run execution ---

    def execute_run(self, args, workingDir=None):
        """
        This method executes the command line and waits for the termination of it,
        handling all setup and cleanup.
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

    def _start_execution(self, *args, **kwargs):
        if not self._use_namespaces:
            return super(ContainerExecutor, self)._start_execution(*args, **kwargs)
        else:
            return self._start_execution_in_container(*args, **kwargs)


    # --- container implementation with namespaces ---

    def _start_execution_in_container(self, args, stdin, stdout, stderr, env, cwd, temp_dir, cgroups,
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
        cwd = cwd or os.path.abspath(os.curdir)

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
                # The state of the threading module may be wrong now, because in the child
                # there is only this one thread. Although we do not need the threading module
                # in the child right now, it should not hurt to correct this state.
                threading._after_fork()
            except Exception:
                pass # But if this fails, we don't care.

            try:
                logging.debug("Child process of RunExecutor started in container with PID %d.",
                              container.get_my_pid_from_procfs())
                if not self._allow_network:
                    container.activate_network_interface("lo")
                self._setup_container_filesystem(temp_dir)

                # Close pipe ends that are not necessary in (grand)child
                os.close(from_grandchild)
                os.close(to_grandchild)

                grandchild_proc = subprocess.Popen(args,
                                    stdin=stdin,
                                    stdout=stdout, stderr=stderr,
                                    env=env, cwd=cwd,
                                    close_fds=True,
                                    preexec_fn=grandchild)

                container.drop_capabilities()

                os.close(from_parent) # close unnecessary end of pipe

                # Set up signal handlers to forward signals to grandchild
                # (because we are PID 1, there is a special signal handling otherwise).
                # cf. dumb-init project: https://github.com/Yelp/dumb-init
                container.forward_all_signals(grandchild_proc.pid, args[0])

                # wait for grandchild and return its result
                grandchild_result = self._wait_for_process(grandchild_proc.pid, args[0])
                logging.debug("Process %s terminated with exit code %d.",
                              args[0], grandchild_result[0])
                os.write(to_parent, pickle.dumps(grandchild_result))
                os.close(to_parent)

                return 0
            except EnvironmentError as e:
                logging.debug("Error in child process of RunExecutor: %s", e)
                try:
                    return int(e.errno)
                except BaseException:
                    # subprocess.Popen in Python 2.7 throws OSError with errno=None
                    # if the preexec_fn fails.
                    return -2
            except:
                # Need to catch everything because this method always needs to return a int
                # (we are inside a C callback that requires returning int).
                logging.exception("Error in child process of RunExecutor")
                return -1

        try: # parent
            child_pid = container.execute_in_namespace(child, use_network_ns=not self._allow_network)

            def check_child_exit_code():
                """Check if the child process terminated cleanly and raise an error otherwise."""
                child_exitcode, unused_child_rusage = self._wait_for_process(child_pid, args[0])
                child_exitcode = util.ProcessExitCode.from_raw(child_exitcode)
                logging.debug("Child process of RunExecutor with PID %d terminated with %s.",
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

            logging.debug("Executing %s in process with PID %d.", args[0], grandchild_pid)

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

            exitcode, ru_child = pickle.loads(received)
            return exitcode, ru_child, parent_cleanup

        return grandchild_pid, wait_for_grandchild

    def _is_below(self, path, target_path):
        # compare with trailing slashes for cases like /foo and /foobar
        path = os.path.join(path, b"")
        target_path = os.path.join(target_path, b"")
        return path.startswith(target_path)

    def _is_special_dir(self, path):
        return (path in self._special_dirs or
            any(self._is_below(path, special_dir) for special_dir in self._special_dirs))

    def _setup_container_filesystem(self, temp_dir):
        """Setup the filesystem layout in the container.
        First, we create a copy of the existing mounts of the system under a new directory
        (either a read-only copy or as an overlay depending on file-system mode), then
        we handle those directories that should be hidden (we mount a fresh directory over them),
        or should stay writable (we add a writable bind mount from the original directory),
        and then we chroot into the new mount hierarchy.

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
        mount_base = os.path.join(temp_dir, b"mount")
        temp_base = os.path.join(temp_dir, b"temp")
        os.mkdir(mount_base)
        os.mkdir(temp_base)

        # Setup new filesystem hierarchy below mount_base.
        if self._filesystem_mode == FS_OVERLAY:
            self._setup_container_filesystem_overlay(temp_dir, mount_base, temp_base)
        else:
            self._setup_container_filesystem_bind(mount_base, temp_base)

        # Handle special directories the user requested.
        for special_dir, kind in self._special_dirs.items():
            mount_path = mount_base + special_dir
            temp_path = temp_base + special_dir
            if not os.path.exists(mount_path):
                os.makedirs(mount_path)
            if kind == DIR_HIDDEN:
                if not os.path.exists(temp_path):
                    os.makedirs(temp_path)
                container.make_bind_mount(temp_path, mount_path)
            elif kind == DIR_WRITABLE:
                container.make_bind_mount(special_dir, mount_path, recursive=True, private=True)

        # If necessary, (i.e., if /tmp is not already hidden),
        # hide the directory where we store our files from processes in the container
        # by mounting an empty directory over it.
        if os.path.exists(mount_base + temp_dir):
            os.makedirs(temp_base + temp_dir)
            container.make_bind_mount(temp_base + temp_dir, mount_base + temp_dir)

        os.chroot(mount_base)

    def _setup_container_filesystem_overlay(self, temp_dir, mount_base, temp_base):
        """Setup the filesystem layout in the container with an overlay filesystem.
        As first step, we create an overlay for "/". Then we bind mount /proc, /dev, and /sys,
        for which overlays do not make sense or do not work.
        Then we create overlays for all other mountpoints (an overlay mount does not recursively
        propagate to sub mounts).

        @param temp_dir: The base directory under which all our directories should be created.
        @param mount_base: The base directory where the container filesystem should be set up
            (we will chroot into this directory).
        @param temp_base: The base directory where temporary files of the tool are created.
        """
        # Overlayfs needs its own additional temporary directory ("work" directory).
        # temp_base will be the "upper" layer, the host FS the "lower" layer,
        # and mount_base the mount target.
        work_base = os.path.join(temp_dir, b"overlayfs")
        os.mkdir(work_base)

        if self._container_system_config:
            container.setup_container_system_config(temp_base)

        # Mount overlay for / in the container
        container.make_overlay_mount(mount_base, b"/", temp_base, work_base)

        # Import /proc from host into the container (necessary for the grandchild to read PID,
        # will be replaced later).
        container.make_bind_mount(b"/proc", os.path.join(mount_base, b"proc"), recursive=True, private=True)
        # Import /dev and /sys from host into the container, overlay does not work well here.
        container.make_bind_mount(b"/dev", os.path.join(mount_base, b"dev"), recursive=True, private=True)
        container.make_bind_mount(b"/sys", os.path.join(mount_base, b"sys"), recursive=True, private=True)

        # Mount all other host FS in the container
        for unused_source, mountpoint, fstype, options in container.get_mount_points():
            if (mountpoint == b"/" or
                    self._is_below(mountpoint, b"/proc") or
                    self._is_below(mountpoint, temp_dir) or
                    self._is_special_dir(mountpoint) or
                    fstype == b"autofs"):
                # Ignore mounts that are handled otherwise or are irrelevant.
                continue

            mount_path = mount_base + mountpoint
            temp_path = temp_base + mountpoint
            work_path = work_base + mountpoint

            if (self._is_below(mountpoint, b"/sys") or
                    self._is_below(mountpoint, b"/dev") or
                    fstype == b"cgroup"):
                # Mark as readonly, because overlay does not make sense for these.
                container.remount_with_additional_flags(mount_path, options, libc.MS_RDONLY)
                continue

            os.makedirs(temp_path)
            os.makedirs(work_path)
            container.make_overlay_mount(mount_path, mountpoint, temp_path, work_path)

    def _setup_container_filesystem_bind(self, mount_base, temp_base):
        """Setup the filesystem layout in the container with bind mounts from the host.
        As first step, we create a copy of all existing mountpoints in mount_base, recursively,
        and as "private" mounts (i.e., changes to existing mountpoints afterwards won't propagate
        to our copy). Then we mark them readonly where necessary.
        Linux does not support making read-only bind mounts in one step:
        https://lwn.net/Articles/281157/ http://man7.org/linux/man-pages/man8/mount.8.html

        @param mount_base: The base directory where the container filesystem should be set up
            (we will chroot into this directory).
        @param temp_base: The base directory where temporary files of the tool are created.
        """
        # First step: create copy of all mounts in mount_base
        container.make_bind_mount(b"/", mount_base, recursive=True, private=True)

        # Second step: mark existing mounts below mount_base as readonly if necessary
        for unused_source, full_mountpoint, unused_fstype, options in container.get_mount_points():
            if not self._is_below(full_mountpoint, mount_base):
                continue
            mountpoint = full_mountpoint[len(mount_base):] or b"/"

            if not (b"ro" in options or self._is_special_dir(mountpoint)):
                # mountpoint is visible in container and should be readonly, mark as such
                container.remount_with_additional_flags(full_mountpoint, options, libc.MS_RDONLY)


if __name__ == '__main__':
    main()
