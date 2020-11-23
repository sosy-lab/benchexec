# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.result as result
import benchexec.tools.template


class Tool(benchexec.tools.template.BaseTool2):
    """
    Tool info for the witness checker (witnesslint)
    (https://github.com/sosy-lab/sv-witnesses)
    """

    REQUIRED_PATHS = ["witnesslint"]

    def executable(self, tool_locator):
        return tool_locator.find_executable("witnesslinter.py")

    def name(self):
        return "witnesslint"

    def version(self, executable):
        version_string = self._version_from_tool(executable)
        return version_string.partition("version")[2].strip().split(" ")[0]

    def _code_matches_tool_output(self, tool_output, exit_code):
        return tool_output[-1] == "Exit code: {}".format(exit_code)

    def determine_result(self, run):
        if run.exit_code.value == 0:
            if self._code_matches_tool_output(run.output, 0):
                return result.RESULT_DONE
        elif run.exit_code.value == 1:
            if self._code_matches_tool_output(run.output, 1):
                return result.RESULT_ERROR + "(invalid witness)"
        return "EXCEPTION"
