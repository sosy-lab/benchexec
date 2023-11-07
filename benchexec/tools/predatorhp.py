# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

from benchexec.tools.sv_benchmarks_util import get_data_model_from_task, ILP32, LP64
import benchexec.tools.template
import benchexec.result as result


class Tool(benchexec.tools.template.BaseTool2):
    """
    Wrapper for a Predator - Hunting Party
    """

    def executable(self, tool_locator):
        return tool_locator.find_executable("predatorHP.py")

    def name(self):
        return "PredatorHP"

    def project_url(self):
        return "https://www.fit.vutbr.cz/research/groups/verifit/tools/predatorhp/"

    def version(self, executable):
        return self._version_from_tool(executable, use_stderr=True)

    def cmdline(self, executable, options, task, rlimits):
        spec = ["--propertyfile", task.property_file] if task.property_file else []

        data_model_param = get_data_model_from_task(
            task,
            {ILP32: "--compiler-options=-m32", LP64: "--compiler-options=-m64"},
        )
        if data_model_param and data_model_param not in options:
            options += [data_model_param]

        return [executable] + options + spec + list(task.input_files_or_identifier)

    def determine_result(self, run):
        status = "UNKNOWN"
        if run.output.any_line_contains("UNKNOWN"):
            status = result.RESULT_UNKNOWN
        elif run.output.any_line_contains("TRUE"):
            status = result.RESULT_TRUE_PROP
        elif run.output.any_line_contains("FALSE(valid-memtrack)"):
            status = result.RESULT_FALSE_MEMTRACK
        elif run.output.any_line_contains("FALSE(valid-deref)"):
            status = result.RESULT_FALSE_DEREF
        elif run.output.any_line_contains("FALSE(valid-free)"):
            status = result.RESULT_FALSE_FREE
        elif run.output.any_line_contains("FALSE(valid-memcleanup)"):
            status = result.RESULT_FALSE_MEMCLEANUP
        elif run.output.any_line_contains("FALSE"):
            status = result.RESULT_FALSE_REACH
        if status == "UNKNOWN" and run.was_timeout:
            status = result.RESULT_TIMEOUT
        return status
