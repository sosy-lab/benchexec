# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0


"""
    This is just for debugging. It wraps the regular benchexec.py located in benchexec folder.
    If you debugg original one you get import errors
"""

"""This module contians the tool benchexec for executing a whole benchmark (suite).
To use it, instantiate the "benchexec.benchexec.BenchExec"
and either call "instance.start()" or "benchexec.benchexec.main(instance)".
"""

import argparse
import datetime
import logging
import os
import sys

from benchexec import __version__
from benchexec import BenchExecException
from benchexec.model import Benchmark
from benchexec.outputhandler import OutputHandler
import benchexec.util as util

from benchexec.benchexec import BenchExec

_BYTE_FACTOR = 1000  # byte in kilobyte


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
        sys.exit("benchexec needs Python 3 to run.")

    try:

        if not benchexec:

            benchexec = BenchExec()

        def signal_stop(signum, frame):
            logging.debug("Received signal %d, terminating.", signum)
            benchexec.stop()

        # Handle termination-request signals that are available on the current platform
        for signal_name in ["SIGINT", "SIGQUIT", "SIGTERM", "SIGBREAK"]:
            util.try_set_signal_handler(signal_name, signal_stop)

        sys.exit(benchexec.start(argv or sys.argv))
    except BenchExecException as e:
        sys.exit("Error: " + str(e))


if __name__ == "__main__":
    main()
