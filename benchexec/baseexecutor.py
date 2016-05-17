# BenchExec is a framework for reliable benchmarking.
# This file is part of BenchExec.
#
# Copyright (C) 2007-2015  Dirk Beyer
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

import errno
import logging
import os
import signal
import subprocess
import sys
import threading
sys.dont_write_bytecode = True # prevent creation of .pyc files

from benchexec import __version__


def add_basic_executor_options(argument_parser):
    """Add some basic options for an executor to an argparse argument_parser."""
    argument_parser.add_argument("args", nargs="+", metavar="ARG",
        help='command line to run (prefix with "--" to ensure all arguments are treated correctly)')
    argument_parser.add_argument("--version", action="version", version="%(prog)s " + __version__)

    verbosity = argument_parser.add_mutually_exclusive_group()
    verbosity.add_argument("--debug", action="store_true",
                           help="show debug output")
    verbosity.add_argument("--quiet", action="store_true",
                           help="show only warnings")

def handle_basic_executor_options(options, parser):
    """Handle the options specified by add_basic_executor_options()."""
    # setup logging
    logLevel = logging.INFO
    if options.debug:
        logLevel = logging.DEBUG
    elif options.quiet:
        logLevel = logging.WARNING
    logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s",
                        level=logLevel)


class BaseExecutor(object):
    """Class for starting and handling processes."""

    def __init__(self):
        self.PROCESS_KILLED = False
        self.SUB_PROCESS_PIDS_LOCK = threading.Lock() # needed, because we kill the process asynchronous
        self.SUB_PROCESS_PIDS = set()

    def _kill_process(self, pid, sig=signal.SIGKILL):
        """Try to send signal to given process."""
        try:
            os.kill(pid, sig)
        except OSError as e:
            if e.errno == errno.ESRCH: # process itself returned and exited before killing
                logging.debug("Failure %s while killing process %s with signal %s: %s",
                              e.errno, pid, sig, e.strerror)
            else:
                logging.warning("Failure %s while killing process %s with signal %s: %s",
                                e.errno, pid, sig, e.strerror)

    def _create_dirs_in_temp_dir(self, *paths):
        """Create some directories, all of which need to be below the temp_dir given to
        _start_execution(). This can be overridden by subclasses if necessary.
        """
        for path in paths:
            os.mkdir(path)

    def _build_cmdline(self, args, env={}):
        """Build the final command line for executing the given command."""
        return args

    def _start_execution(self, args, stdin, stdout, stderr, env, cwd, temp_dir, cgroups,
                         parent_setup_fn, child_setup_fn, parent_cleanup_fn):
        """Actually start the tool and the measurements.
        @param parent_setup_fn a function without parameters that is called in the parent process
            immediately before the tool is started
        @param child_setup_fn a function without parameters that is called in the child process
            before the tool is started
        @param parent_cleanup_fn a function with one positional parameter that is called in the
            parent process immediately after the tool terminated, with the result of
            parent_setup_fn as parameter value
        @return: a tuple of PID of process and a blocking function, which waits for the process
            and a triple of the exit code and the resource usage of the process
            and the result of parent_cleanup_fn (do not use os.wait)
        """
        def pre_subprocess():
            # Do some other setup the caller wants.
            child_setup_fn()

            # put us into the cgroup(s)
            pid = os.getpid()
            cgroups.add_task(pid)

        # Set HOME and TMPDIR to fresh directories.
        tmp_dir = os.path.join(temp_dir, "tmp")
        home_dir = os.path.join(temp_dir, "home")
        self._create_dirs_in_temp_dir(tmp_dir, home_dir)
        env["HOME"] = home_dir
        env["TMPDIR"] = tmp_dir
        env["TMP"] = tmp_dir
        env["TEMPDIR"] = tmp_dir
        env["TEMP"] = tmp_dir
        logging.debug("Executing run with $HOME and $TMPDIR below %s.", temp_dir)

        args = self._build_cmdline(args, env=env)

        parent_setup = parent_setup_fn()

        p = subprocess.Popen(args,
                     stdin=stdin,
                     stdout=stdout, stderr=stderr,
                     env=env, cwd=cwd,
                     close_fds=True,
                     preexec_fn=pre_subprocess)

        def wait_and_get_result():
            exitcode, ru_child = self._wait_for_process(p.pid, args[0])

            parent_cleanup = parent_cleanup_fn(parent_setup)
            return exitcode, ru_child, parent_cleanup

        return p.pid, wait_and_get_result


    def _wait_for_process(self, pid, name):
        """Wait for the given process to terminate.
        @return tuple of exit code and resource usage
        """
        try:
            logging.debug("Waiting for process %s with pid %s", name, pid)
            unused_pid, exitcode, ru_child = os.wait4(pid, 0)
            return exitcode, ru_child
        except OSError as e:
            if self.PROCESS_KILLED and e.errno == errno.EINTR:
                # Interrupted system call seems always to happen
                # if we killed the process ourselves after Ctrl+C was pressed
                # We can try again to get exitcode and resource usage.
                logging.debug("OSError %s while waiting for termination of %s (%s): %s.",
                              e.errno, name, pid, e.strerror)
                try:
                    unused_pid, exitcode, ru_child = os.wait4(pid, 0)
                    return exitcode, ru_child
                except OSError:
                    pass # original error will be handled and this ignored

            logging.critical("OSError %s while waiting for termination of %s (%s): %s.",
                             e.errno, name, pid, e.strerror)
            return (0, None)

    def stop(self):
        self.PROCESS_KILLED = True
        with self.SUB_PROCESS_PIDS_LOCK:
            for pid in self.SUB_PROCESS_PIDS:
                logging.warning('Killing process %s forcefully.', pid)
                try:
                    self._kill_process(pid)
                except EnvironmentError as e:
                    # May fail due to race conditions
                    logging.debug(e)
