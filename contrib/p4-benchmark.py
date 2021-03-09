import sys
import logging

from benchexec import util as util
from benchexec.benchexec import BenchExec
from benchexec.model import BenchExecException

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