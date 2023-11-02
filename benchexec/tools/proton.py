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

    def cmdline(self, executable, options, task, rlimits):
        if task.property_file:
            options = options + ["--propertyFile", task.property_file]

        data_model_param = get_data_model_from_task(task, {ILP32: "32", LP64: "64"})
        if data_model_param and data_model_param not in options:
            options += [data_model_param]

        self.options = options

        return [executable] + options + list(task.input_files_or_identifier)

    def determine_result(self, run):
        output = run.output

        if run.exit_code.value in [0, 10]:
            status = result.RESULT_ERROR
            if len(output) > 0:
                # SV-COMP mode
                result_str = output[-1].strip()

                if result_str == "TRUE":
                    status = result.RESULT_TRUE_PROP
                elif "FALSE" in result_str:
                    if result_str == "FALSE(termination)":
                        status = result.RESULT_FALSE_TERMINATION
                    else:
                        status = result.RESULT_FALSE_REACH
                elif "UNKNOWN" in output:
                    status = result.RESULT_UNKNOWN

        elif run.exit_code.value == 64 and "Usage error!" in output:
            status = "INVALID ARGUMENTS"

        elif run.exit_code.value == 6 and "Out of memory" in output:
            status = "OUT OF MEMORY"

        elif run.exit_code.value == 6 and "SAT or SMT checker error: out-of-memory or internal-error" in output:
            status = "OUT-OF-MEMORY or INTERNAL-ERROR"

        else:
            status = result.RESULT_ERROR

        return status
