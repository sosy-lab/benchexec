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
    Tool info for Deagle, an SMT-based concurrent program verification tool.
        Project URL: https://github.com/Misasasa/Deagle
    """

    def executable(self, tool_locator):
        return tool_locator.find_executable("deagle")

    def name(self):
        return "Deagle"

    def version(self, executable):
        return self._version_from_tool(executable)

    def get_data_model(self, task):
        if isinstance(task.options, dict) and task.options.get("language") == "C":
            data_model = task.options.get("data_model")
            if data_model == "ILP32":
                return ["--32"]
            elif data_model == "LP64":
                return ["--64"]
            else:
                raise benchexec.tools.template.UnsupportedFeatureException(
                    f"Unsupported data_model '{data_model}' defined for task '{task}'"
                )

        return ["--32"]  # default

    def cmdline(self, executable, options, task, rlimits):
        return (
            [executable]
            + options
            + self.get_data_model(task)
            + [task.single_input_file]
        )

    def determine_result(self, run):
        stroutput = run.output.text

        if run.output.any_line_contains("SUCCESSFUL"):
            status = result.RESULT_TRUE_PROP
        elif run.output.any_line_contains("FAILED"):
            status = result.RESULT_FALSE_REACH
        elif run.exit_code.value == 1:
            status = result.RESULT_UNKNOWN
        else:
            status = result.RESULT_ERROR

        return status
