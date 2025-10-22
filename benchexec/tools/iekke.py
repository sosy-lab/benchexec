# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

from benchexec.tools.sv_benchmarks_util import get_data_model_from_task, ILP32, LP64
import benchexec.result as result
import benchexec.tools.template


class Tool(benchexec.tools.template.BaseTool2):
    """
    Tool info for iekke, a SAT-based concurrent program verification tool.
    """

    def version(self, executable):
        return self._version_from_tool(executable, arg="--version")

    def executable(self, tool_locator):
        exe = tool_locator.find_executable("iekke")
        return exe

    def name(self):
        return "iekke"

    def project_url(self):
        return "https://github.com/paolo-di-biase/Lazy-PO"

    def cmdline(self, executable, options, task, rlimits):
        data_model_param = get_data_model_from_task(task, {ILP32: "--32", LP64: "--64"})
        if not data_model_param:
            data_model_param = "--32"
        return (
            [executable]
            + [task.property_file]
            + [task.single_input_file]
            + [data_model_param]
        )

    def determine_result(self, run):
        if run.output.any_line_contains("SUCCESSFUL"):
            status = result.RESULT_TRUE_PROP
        elif run.output.any_line_contains("FAILED"):
            status = result.RESULT_FALSE_REACH
            for line in run.output:
                if "nodatarace.assertion." in line and "FAILURE" in line:
                    status = result.RESULT_FALSE_DATARACE
                if (
                    "alloc.assertion." in line or "pointer_dereference." in line
                ) and "FAILURE" in line:
                    status = result.RESULT_FALSE_DEREF
                if "memory-leak." in line and "FAILURE" in line:
                    status = result.RESULT_FALSE_MEMTRACK
                if "overflow." in line and "FAILURE" in line:
                    status = result.RESULT_FALSE_OVERFLOW
        elif run.exit_code.value == 1:
            status = result.RESULT_UNKNOWN
        else:
            status = result.RESULT_ERROR

        return status
