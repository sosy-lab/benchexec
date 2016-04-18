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

"""This module contians the tool benchexec for executing a whole benchmark (suite).
To use it, instantiate the "benchexec.benchexec.BenchExec"
and either call "instance.start()" or "benchexec.benchexec.main(instance)".
"""

# prepare for Python 3
from __future__ import absolute_import, division, print_function, unicode_literals

import argparse
import logging
import os
import signal
import sys
import time

from benchexec import __version__
from benchexec.model import Benchmark
from benchexec import containerexecutor
from benchexec.outputhandler import OutputHandler
from benchexec import util

_BYTE_FACTOR = 1000 # byte in kilobyte

class BenchExec(object):
    """
    The main class of BenchExec.
    It is designed to be extended by inheritance, and for example
    allows configuration options to be added and the executor to be replaced.
    By default, it uses an executor that executes all runs on the local machine.
    """

    DEFAULT_OUTPUT_PATH = "results/"

    def __init__(self):
        self.executor = None
        self.stopped_by_interrupt = False

    def start(self, argv):
        """
        Start BenchExec.
        @param argv: command-line options for BenchExec
        """
        parser = self.create_argument_parser()
        self.config = parser.parse_args(argv[1:])

        for arg in self.config.files:
            if not os.path.exists(arg) or not os.path.isfile(arg):
                parser.error("File {0} does not exist.".format(repr(arg)))

        if os.path.isdir(self.config.output_path):
            self.config.output_path = os.path.normpath(self.config.output_path) + os.sep

        self.setup_logging()

        self.executor = self.load_executor()

        returnCode = 0
        for arg in self.config.files:
            if self.stopped_by_interrupt:
                break
            logging.debug("Benchmark %r is started.", arg)
            rc = self.execute_benchmark(arg)
            returnCode = returnCode or rc
            logging.debug("Benchmark %r is done.", arg)

        logging.debug("I think my job is done. Have a nice day!")
        return returnCode


    def create_argument_parser(self):
        """
        Create a parser for the command-line options.
        May be overwritten for adding more configuration options.
        @return: an argparse.ArgumentParser instance
        """
        parser = argparse.ArgumentParser(
            fromfile_prefix_chars='@',
            description=
            """Execute benchmarks for a given tool with a set of input files.
               Benchmarks are defined in an XML file given as input.
               Command-line parameters can additionally be read from a file if file name prefixed with '@' is given as argument.
               The tool table-generator can be used to create tables for the results.
               Part of BenchExec: https://github.com/sosy-lab/benchexec/""")

        parser.add_argument("files", nargs='+', metavar="FILE",
                          help="XML file with benchmark definition")
        parser.add_argument("-d", "--debug",
                          action="store_true",
                          help="Enable debug output and a debugging helper on signal USR1")

        parser.add_argument("-r", "--rundefinition", dest="selected_run_definitions",
                          action="append",
                          help="Run only the specified RUN_DEFINITION from the benchmark definition file. "
                                + "This option can be specified several times and can contain wildcards.",
                          metavar="RUN_DEFINITION")

        parser.add_argument("-t", "--tasks", dest="selected_sourcefile_sets",
                          action="append",
                          help="Run only the tasks from the tasks tag with TASKS as name. "
                                + "This option can be specified several times and can contain wildcards.",
                          metavar="TASKS")

        parser.add_argument("-n", "--name",
                          dest="name", default=None,
                          help="Set name of benchmark execution to NAME",
                          metavar="NAME")

        parser.add_argument("-o", "--outputpath",
                          dest="output_path", type=str,
                          default=self.DEFAULT_OUTPUT_PATH,
                          help="Output prefix for the generated results. "
                                + "If the path is a folder files are put into it,"
                                + "otherwise it is used as a prefix for the resulting files.")

        parser.add_argument("-T", "--timelimit",
                          dest="timelimit", default=None,
                          help='Time limit for each run, e.g. "90s" '
                               '(overwrites time limit and hard time limit from XML file, '
                               'use "-1" to disable time limits completely)',
                          metavar="SECONDS")

        parser.add_argument("-M", "--memorylimit",
                          dest="memorylimit", default=None,
                          help="Memory limit, if no unit is given MB are assumed (-1 to disable)",
                          metavar="BYTES")

        parser.add_argument("-N", "--numOfThreads",
                          dest="num_of_threads", default=None, type=int,
                          help="Run n benchmarks in parallel",
                          metavar="n")

        parser.add_argument("-c", "--limitCores", dest="corelimit",
                          default=None,
                          metavar="N",
                          help="Limit each run of the tool to N CPU cores (-1 to disable).")

        parser.add_argument("--user",
                            dest="users",
                            action="append",
                            metavar="USER",
                            help="Execute benchmarks under given user account(s) (needs password-less sudo setup).")

        parser.add_argument("--no-compress-results",
                            dest="compress_results", action="store_false",
                            help="Do not compress result files.")

        def parse_filesize_value(value):
            try:
                value = int(value)
                if value == -1:
                    return None
                logging.warning(
                    'Value "%s" for logfile size interpreted as MB for backwards compatibility, '
                    'specify a unit to make this unambiguous.',
                    value)
                value = value * _BYTE_FACTOR * _BYTE_FACTOR
            except ValueError:
                value = util.parse_memory_value(value)
            return value

        parser.add_argument("--maxLogfileSize", dest="maxLogfileSize",
                            type=parse_filesize_value, default=20*_BYTE_FACTOR*_BYTE_FACTOR,
                            metavar="SIZE",
                            help="Shrink logfiles to given size if they are too big. "
                                 "(-1 to disable, default value: 20 MB).")

        parser.add_argument("--commit", dest="commit",
                          action="store_true",
                          help="If the output path is a git repository without local changes, "
                                + "add and commit the result files.")

        parser.add_argument("--message",
                          dest="commit_message", type=str,
                          default="Results for benchmark run",
                          help="Commit message if --commit is used.")

        parser.add_argument("--startTime",
                          dest="start_time",
                          type=parse_time_arg,
                          default=None,
                          metavar="'YYYY-MM-DD hh:mm'",
                          help='Set the given date and time as the start time of the benchmark.')

        parser.add_argument("--version",
                            action="version",
                            version="%(prog)s " + __version__)

        container_args = parser.add_argument_group("optional arguments for run container")
        container_on_args = container_args.add_mutually_exclusive_group()
        container_on_args.add_argument("--container", action='store_true',
            help="force isolation of run in container (future default starting with BenchExec 2.0)")
        container_on_args.add_argument("--no-container", action='store_true',
            help="disable use of containers for isolation of runs (current default)")
        containerexecutor.add_basic_container_args(container_args)

        return parser


    def setup_logging(self):
        """
        Configure the logging framework.
        """
        if self.config.debug:
            logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s",
                                level=logging.DEBUG)
            util.activate_debug_shell_on_signal()
        else:
            logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s",
                                level=logging.INFO)


    def load_executor(self):
        """
        Create and return the executor module that should be used for benchmarking.
        May be overridden for replacing the executor,
        for example with an implementation that delegates to some cloud service.
        """
        from . import localexecution as executor
        return executor


    def execute_benchmark(self, benchmark_file):
        """
        Execute a single benchmark as defined in a file.
        If called directly, ensure that config and executor attributes are set up.
        @param benchmark_file: the name of a benchmark-definition XML file
        @return: a result value from the executor module
        """
        benchmark = Benchmark(benchmark_file, self.config,
                              self.config.start_time or time.localtime())
        self.check_existing_results(benchmark)

        self.executor.init(self.config, benchmark)
        output_handler = OutputHandler(benchmark, self.executor.get_system_info(),
                                       self.config.compress_results)

        logging.debug("I'm benchmarking %r consisting of %s run sets.",
                      benchmark_file, len(benchmark.run_sets))

        try:
            result = self.executor.execute_benchmark(benchmark, output_handler)
        finally:
            output_handler.close()
            # remove useless log folder if it is empty
            try:
                os.rmdir(benchmark.log_folder)
            except:
                pass

        if self.config.commit and not self.stopped_by_interrupt:
            try:
                util.add_files_to_git_repository(self.config.output_path,
                        output_handler.all_created_files,
                        self.config.commit_message+'\n\n'+output_handler.description)
            except OSError as e:
                logging.warning('Could not add files to git repository: %s', e)
        return result


    def check_existing_results(self, benchmark):
        """
        Check and abort if the target directory for the benchmark results
        already exists in order to avoid overwriting results.
        """
        if os.path.exists(benchmark.log_folder):
            sys.exit('Output directory {0} already exists, will not overwrite existing results.'.format(benchmark.log_folder))
        if os.path.exists(benchmark.log_zip):
            sys.exit('Output archive {0} already exists, will not overwrite existing results.'.format(benchmark.log_zip))


    def stop(self):
        """
        Stop the execution of a benchmark.
        This instance cannot be used anymore afterwards.
        Timely termination is not guaranteed, and this method may return before
        everything is terminated.
        """
        self.stopped_by_interrupt = True

        if self.executor:
            self.executor.stop()


def parse_time_arg(s):
    """
    Parse a time stamp in the "year-month-day hour-minute" format.
    """
    try:
        return time.strptime(s, "%Y-%m-%d %H:%M")
    except ValueError as e:
        raise argparse.ArgumentTypeError(e)


def signal_handler_ignore(signum, frame):
    """
    Log and ignore all signals.
    """
    logging.warning('Received signal %d, ignoring it.', signum)

def main(benchexec=None, argv=None):
    """
    The main method of BenchExec for use in a command-line script.
    In addition to calling benchexec.start(argv),
    it also handles signals and keyboard interrupts.
    It does not return but calls sys.exit().
    @param benchexec: An instance of BenchExec for executing benchmarks.
    @param argv: optionally the list of command-line options to use
    """
    if sys.version_info < (3,):
        sys.exit('benchexec needs Python 3 to run.')
    # ignore SIGTERM
    signal.signal(signal.SIGTERM, signal_handler_ignore)
    try:
        if not benchexec:
            benchexec = BenchExec()
        sys.exit(benchexec.start(argv or sys.argv))
    except KeyboardInterrupt: # this block is reached, when interrupt is thrown before or after a run set execution
        benchexec.stop()
        util.printOut("\n\nScript was interrupted by user, some runs may not be done.")

if __name__ == '__main__':
    main()
