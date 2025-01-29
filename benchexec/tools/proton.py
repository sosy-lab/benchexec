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
    PROTON
    """

    def executable(self, tool_locator):
        return tool_locator.find_executable("proton")

    def version(self, executable):
        return self._version_from_tool(executable, use_stderr=True)

    def name(self):
        return "PROTON"

    def project_url(self):
        return "https://github.com/kumarmadhukar/term"

    def cmdline(self, executable, options, task, rlimits):
        if task.property_file:
            options = options + ["--propertyFile", task.property_file]

        data_model_param = get_data_model_from_task(task, {ILP32: "32", LP64: "64"})
        if data_model_param and data_model_param not in options:
            options += [data_model_param]

        return [executable] + options + [task.single_input_file]

    def determine_result(self, run):
        if run.exit_code.value not in [0, 10] or len(run.output) == 0:
            return result.RESULT_ERROR

        result_str = run.output[-1].strip()

        if result_str == "TRUE":
            return result.RESULT_TRUE_PROP

        elif "FALSE(termination)" in result_str:
            return result.RESULT_FALSE_TERMINATION

        elif "UNKNOWN" in result_str:
            return result.RESULT_UNKNOWN

        elif "INTERNAL-ERROR" in result_str:
            return "INTERNAL-ERROR"

        elif "OUT OF MEMORY" in result_str:
            return "OUT OF MEMORY"

        elif "INCONCLUSIVE" in result_str:
            return "INCONCLUSIVE"

        elif "UNRECOGNIZED PROPERTY" in result_str:
            return "UNSUPPORTED PROPERTY SPECIFIED"

        return result.RESULT_ERROR
