# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.result as result
import benchexec.tools.template


class Smtlib2Tool(benchexec.tools.template.BaseTool):
    """
    Abstract base class for tool infos for SMTLib2-compatible solvers.
    These tools share a common output format, which is implemented here.
    """

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        if returnsignal == 0 and returncode == 0:
            status = None
            for line in output:
                line = line.strip()
                if line == "unsat":
                    status = result.RESULT_FALSE_PROP
                elif line == "sat":
                    status = result.RESULT_TRUE_PROP
                elif not status and line.startswith("(error "):
                    status = "ERROR"

            if not status:
                status = result.RESULT_UNKNOWN

        elif ((returnsignal == 9) or (returnsignal == 15)) and isTimeout:
            status = result.RESULT_TIMEOUT

        elif returnsignal == 9:
            status = "KILLED BY SIGNAL 9"
        elif returnsignal == 6:
            status = "ABORTED"
        elif returnsignal == 15:
            status = "KILLED"
        else:
            status = f"ERROR ({returncode})"

        return status
