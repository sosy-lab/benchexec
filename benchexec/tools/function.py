# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2025 Naïm MOUSSAOUI REMIL
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.result as result
import benchexec.tools.template
from benchexec.tools.sv_benchmarks_util import (
    TaskFilesConsidered,
    handle_witness_of_task,
)


class Tool(benchexec.tools.template.BaseTool2):
    """
    Tool info for FuncTion.
    """

    def executable(self, tool_locator):
        return tool_locator.find_executable("function.exe")

    def version(self, executable):
        return self._version_from_tool(executable)

    def name(self):
        return "FuncTion"

    def project_url(self):
        return "https://github.com/naim-mr/function"

    def cmdline(self, executable, options, task, rlimits):
        input_files, witness_options = handle_witness_of_task(
            task,
            options,
            "--validate_yaml_witness",
            TaskFilesConsidered.INPUT_FILES,
        )
        cmd = [executable] + input_files 
        return cmd + list(options)

    def determine_result(self, run):
        if run.was_timeout:
            return result.RESULT_TIMEOUT
        if not run.output:
         return result.RESULT_ERROR
        r = run.output[-1] or run.output[-2]  # last non-empty line
        if "Final Analaysis Result: TRUE" in r:
            return result.RESULT_TRUE_PROP
        elif "Final Analaysis Result: false(TERM)" in r:
            return result.RESULT_FALSE_TERMINATION
        else:
            return result.RESULT_UNKNOWN
