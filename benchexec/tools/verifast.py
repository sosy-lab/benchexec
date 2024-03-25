# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2023 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.result as result
import benchexec.tools.template


class Tool(benchexec.tools.template.BaseTool2):
    """
    Tool info module for VeriFast (https://github.com/verifast/verifast)
    """

    def executable(self, tool_locator):
        return tool_locator.find_executable("verifast", subdir="bin")

    def name(self):
        return "VeriFast"

    def version(self, executable):
        return self._version_from_tool(executable)

    def determine_result(self, run):
        for line in run.output:
            line = line.strip()
            if line.startswith("0 errors found"):
                return result.RESULT_TRUE_PROP
            elif "Assertion might not hold." in line:
                return result.RESULT_UNKNOWN
            elif "Callee must have contract" in line:
                return result.RESULT_ERROR + "(underspec)"
            elif line.endswith(": dead code"):
                return result.RESULT_ERROR + "(dead code)"
            elif line.endswith(": Parse error."):
                return result.RESULT_ERROR + "(parse error)"
            elif ": Cannot prove condition." in line:
                return result.RESULT_ERROR + "(cannot prove condition)"
        return result.RESULT_ERROR + "(unknown)"
