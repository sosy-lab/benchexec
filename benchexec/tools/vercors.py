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
    Tool info for VerCors (https://github.com/utwente-fmt/vercors)
    """

    def executable(self, tool_locator):
        return tool_locator.find_executable("vct", subdir="bin")

    def name(self):
        return "VerCors"

    def version(self, executable):
        return self._version_from_tool(executable)

    def determine_result(self, run):
        for line in run.output:
            line = line.strip()
            if line == "[INFO] Verification completed successfully.":
                return result.RESULT_TRUE_PROP
            elif "Parsing failed" in line:
                return result.RESULT_ERROR + "(Parsing failed)"
            elif "Exception in thread" in line:
                return result.RESULT_ERROR + "(Exception)"
            elif "is not supported" in line:
                return result.RESULT_ERROR + "(Unsupported)"
            elif line.startswith("[ERROR]") or "An error condition was reached" in line:
                return result.RESULT_ERROR
        return result.RESULT_UNKNOWN
