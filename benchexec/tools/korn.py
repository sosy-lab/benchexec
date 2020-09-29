# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0


import re
import benchexec.util as util
import benchexec.result as result
import benchexec.tools.template


class Tool(benchexec.tools.template.BaseTool):
    """
    Tool info for Korn, a software verifier based on Horn-clauses.
    URL: https://github.com/gernst/korn
    """

    REQUIRED_PATHS = [
        "run",
        "korn.jar",
        "z3",
        "eld",
        "eld.jar",
    ]

    def executable(self):
        return util.find_executable("run")

    def version(self, executable):
        return self._version_from_tool(executable)

    def name(self):
        return "Korn"

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        """
        This is literally the output from the underlying CHC solver
        """

        for line in output:
            line = line.strip()
            if line == "unsat":
                return result.RESULT_FALSE_PROP
            elif line == "sat":
                return result.RESULT_TRUE_PROP
            elif "error" in line:
                return "ERROR"

        return result.RESULT_UNKNOWN
