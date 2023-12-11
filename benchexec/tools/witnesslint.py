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
    """

    REQUIRED_PATHS = ["witnesslint"]

    def executable(self, tool_locator):
        return tool_locator.find_executable("witnesslinter.py")

    def name(self):
        return "witnesslint"

    def project_url(self):
        return "https://github.com/sosy-lab/sv-witnesses"

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
        witness_type_match = self.get_value_from_output(
            run.output, "Witness Type-Match"
        )
        witness_version_match = self.get_value_from_output(
            run.output, "Witness Version-Match"
        )

        if not run.output:
            return result.RESULT_ERROR + " (no output)"
        elif exit_code == 7 or any(line.startswith("Traceback") for line in run.output):
            return "EXCEPTION"
        elif "witnesslint finished" not in run.output[-1]:
            return result.RESULT_ERROR + " (linter did not finish)"
        elif exit_code == 1:
            return result.RESULT_ERROR + " (invalid witness syntax)"
        elif exit_code == 5:
            return result.RESULT_ERROR + " (witness does not exist)"
        elif exit_code == 6:
            return result.RESULT_ERROR + " (program does not exist)"
        elif witness_type_match == "False":
            return result.RESULT_ERROR + " (unexpected witness type)"
        elif witness_version_match == "False":
            return result.RESULT_ERROR + " (unexpected witness version)"
        elif exit_code == 0:
            return result.RESULT_DONE

        return result.RESULT_ERROR + " (could not determine output)"
