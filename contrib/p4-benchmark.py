# SPDX-FileCopyrightText: 2020-2021 CASTOR Software Research Centre
# <https://www.castor.kth.se/>
# SPDX-FileCopyrightText: 2020-2021 Johan Paulsson

# SPDX-License-Identifier: Apache-2.0

# For instructions on how to use this program, se README in /p4.

import sys
import logging
import os
import benchexec.util as util

from benchexec.benchexec import BenchExecException
from benchexec.benchexec import BenchExec


class P4BenchExec(BenchExec):
    """
    Extension of the basic BenchExec. It overrides the executor and
    changes it to the p4execution executor to examine p4 programs.
    """

    def __init__(self):
        BenchExec.__init__(self)

    def load_executor(self):
        from p4.p4execution import P4Execution

        return P4Execution()


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

    if os.getuid() != 0:
        sys.exit("p4-benchmark needs root access to run")
    try:
        if not benchexec:
            benchexec = P4BenchExec()

        def signal_stop(signum, frame):
            logging.debug("Received signal %d, terminating.", signum)
            benchexec.stop()

        # Handle termination-request signals that are available on the current platform
        for signal_name in ["SIGINT", "SIGQUIT", "SIGTERM", "SIGBREAK"]:
            util.try_set_signal_handler(signal_name, signal_stop)

        sys.exit(benchexec.start(argv or sys.argv))
    except BenchExecException as e:
        sys.exit(f"Error: {e}")


if __name__ == "__main__":
    main()
