# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2025 Naïm MOUSSAOUI REMIL
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.result as result
import benchexec.tools.template


class Tool(benchexec.tools.template.BaseTool2):
    """
    Tool info for FuncTion-Res.
    """

    def executable(self, tool_locator):
        return tool_locator.find_executable("function.exe")

    def version(self, executable):
        return self._version_from_tool(executable, arg="--version")

    def name(self):
        return "FuncTion-Res"

    def project_url(self):
        return "https://github.com/naim-mr/function-res"

    def cmdline(self, executable, options, task, rlimits):
        cmd = [executable] + [task.single_input_file] + options
        return cmd

    def determine_result(self, run):
        if not run.output:
            return result.RESULT_ERROR
        if run.output.any_line_contains("Final Analysis Result: TRUE"):
            return result.RESULT_TRUE_PROP
        elif run.output.any_line_contains("Final Analysis Result: false(TERM)"):
            return result.RESULT_FALSE_TERMINATION
        elif run.output.any_line_contains("Final Analysis Result: UNKNOWN"):
            return result.RESULT_UNKNOWN
        else:
            return result.RESULT_ERROR
