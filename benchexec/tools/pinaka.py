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
    def executable(self, tool_locator):
        return tool_locator.find_executable("pinaka-wrapper.sh")

    def version(self, executable):
        return self._version_from_tool(executable)

    def name(self):
        return "Pinaka"

    def cmdline(self, executable, options, task, rlimits):
        if task.property_file:
            options = options + ["--propertyfile", task.property_file]
        data_model_param = get_data_model_from_task(task, {ILP32: "--32", LP64: "--64"})
        if data_model_param and data_model_param not in options:
            options += [data_model_param]

        return [executable] + options + list(task.input_files_or_identifier)

    def determine_result(self, run):
        status = ""

        if run.exit_code.value in [0, 10]:
            if "VERIFICATION FAILED (ReachSafety)" in run.output:
                status = result.RESULT_FALSE_REACH
            elif "VERIFICATION FAILED (NoOverflow)" in run.output:
                status = result.RESULT_FALSE_OVERFLOW
            elif "VERIFICATION SUCCESSFUL" in run.output:
                status = result.RESULT_TRUE_PROP
            else:
                status = result.RESULT_UNKNOWN
        else:
            status = result.RESULT_ERROR

        return status
