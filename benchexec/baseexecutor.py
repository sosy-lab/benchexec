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

sys.dont_write_bytecode = True  # prevent creation of .pyc files

from benchexec import __version__
from benchexec import util


def add_basic_executor_options(argument_parser):
    """Add some basic options for an executor to an argparse argument_parser."""
    argument_parser.add_argument(
        "args",
        nargs="+",
        metavar="ARG",
        help='command line to run (prefix with "--" to ensure all arguments are treated correctly)',
    )
    argument_parser.add_argument(
        "--version", action="version", version="%(prog)s " + __version__
    )

    verbosity = argument_parser.add_mutually_exclusive_group()
    verbosity.add_argument("--debug", action="store_true", help="show debug output")
    verbosity.add_argument("--quiet", action="store_true", help="show only warnings")


def handle_basic_executor_options(options, parser):
    """Handle the options specified by add_basic_executor_options()."""
    # setup logging
    logLevel = logging.INFO
    if options.debug:
        logLevel = logging.DEBUG
    elif options.quiet:
        logLevel = logging.WARNING
    util.setup_logging(level=logLevel)


class BaseExecutor(object):
    """Class for starting and handling processes."""

    def __init__(self):
        self.PROCESS_KILLED = False
        # killing process is triggered asynchronously, need a lock for synchronization
        self.SUB_PROCESS_PIDS_LOCK = threading.Lock()
        self.SUB_PROCESS_PIDS = set()

    def _get_result_files_base(self, temp_dir):
        """Given the temp directory that is created for each run, return the path to the directory
        where files created by the tool are stored."""
        return temp_dir

    def _start_execution(
        self,
        args,
        stdin,
        stdout,
        stderr,
        env,
        cwd,
        temp_dir,
        cgroups,
        parent_setup_fn,
        child_setup_fn,
        parent_cleanup_fn,
    ):
        """Actually start the tool and the measurements.
        @param parent_setup_fn a function without parameters that is called in the parent process
            immediately before the tool is started
        @param child_setup_fn a function without parameters that is called in the child process
            before the tool is started
        @param parent_cleanup_fn a function that is called in the parent process
            immediately after the tool terminated, with three parameters:
            the result of parent_setup_fn, the result of the executed process as ProcessExitCode,
            and the base path for looking up files as parameter values
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
        os.mkdir(tmp_dir)
        os.mkdir(home_dir)
        env["HOME"] = home_dir
        env["TMPDIR"] = tmp_dir
        env["TMP"] = tmp_dir
        env["TEMPDIR"] = tmp_dir
        env["TEMP"] = tmp_dir
        logging.debug("Executing run with $HOME and $TMPDIR below %s.", temp_dir)

        parent_setup = parent_setup_fn()

        p = subprocess.Popen(
            args,
            stdin=stdin,
            stdout=stdout,
            stderr=stderr,
            env=env,
            cwd=cwd,
            close_fds=True,
            preexec_fn=pre_subprocess,
        )

        def wait_and_get_result():
            exitcode, ru_child = self._wait_for_process(p.pid, args[0])

            parent_cleanup = parent_cleanup_fn(
                parent_setup, util.ProcessExitCode.from_raw(exitcode), ""
            )
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
                logging.debug(
                    "OSError %s while waiting for termination of %s (%s): %s.",
                    e.errno,
                    name,
                    pid,
                    e.strerror,
                )
                try:
                    unused_pid, exitcode, ru_child = os.wait4(pid, 0)
                    return exitcode, ru_child
                except OSError:
                    pass  # original error will be handled and this ignored

            logging.critical(
                "OSError %s while waiting for termination of %s (%s): %s.",
                e.errno,
                name,
                pid,
                e.strerror,
            )
            return 0, None

    def stop(self):
        self.PROCESS_KILLED = True
        with self.SUB_PROCESS_PIDS_LOCK:
            for pid in self.SUB_PROCESS_PIDS:
                logging.warning("Killing process %s forcefully.", pid)
                try:
                    util.kill_process(pid)
                except EnvironmentError as e:
                    # May fail due to race conditions
                    logging.debug(e)
