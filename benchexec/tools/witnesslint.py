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

    def get_value_from_output(self, output, identifier):
        for line in output:
            if line.startswith(identifier):
                return line.split(":", maxsplit=1)[-1].strip()
        return None

    def determine_result(self, run):
        exit_code = run.exit_code.value
        if "witnesslint finished" not in run.output[-1] or exit_code == 7:
            return "EXCEPTION"
        elif exit_code == 0:
            return result.RESULT_DONE
        elif exit_code == 1:
            return result.RESULT_ERROR + " (invalid witness syntax)"
        elif exit_code == 5:
            return result.RESULT_ERROR + " (witness does not exist)"
        elif exit_code == 6:
            return result.RESULT_ERROR + " (program does not exist)"
        else:
            return result.UNKNOWN
