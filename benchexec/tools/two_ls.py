# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.util as util
import benchexec.tools.template
import benchexec.result as result


class Tool(benchexec.tools.template.BaseTool2):
    """
    Wrapper for 2LS (http://www.cprover.org/2LS).
    """

    REQUIRED_PATHS = ["2ls", "2ls-binary", "goto-cc"]

    def executable(self, tool_locator):
        return tool_locator.find_executable("2ls")

    def name(self):
        return "2LS"

    def version(self, executable):
        return self._version_from_tool(executable)

    def cmdline(self, executable, options, task, rlimits):
        if task.property_file:
            options = options + ["--propertyfile", task.property_file]

        data_model_param = util.get_data_model_from_task(
            task, {"ILP32": "--32", "LP64": "--64"}
        )
        if data_model_param and data_model_param not in options:
            options += [data_model_param]

        return [executable] + options + list(task.input_files_or_identifier)

    def determine_result(self, run):
        returnsignal = run.exit_code.signal or 0
        returncode = run.exit_code.value or 0
        if ((returnsignal == 9) or (returnsignal == 15)) and run.was_timeout:
            status = "TIMEOUT"
        elif returnsignal == 9:
            status = "OUT OF MEMORY"
        elif returnsignal != 0:
            status = "ERROR(SIGNAL " + str(returnsignal) + ")"
        elif returncode == 0:
            status = result.RESULT_TRUE_PROP
        elif returncode == 10:
            if len(run.output) > 0:
                result_str = run.output[-1].strip()
                if result_str == "FALSE(valid-memtrack)":
                    status = result.RESULT_FALSE_MEMTRACK
                elif result_str == "FALSE(valid-deref)":
                    status = result.RESULT_FALSE_DEREF
                elif result_str == "FALSE(valid-free)":
                    status = result.RESULT_FALSE_FREE
                elif result_str == "FALSE(no-overflow)":
                    status = result.RESULT_FALSE_OVERFLOW
                elif result_str == "FALSE(termination)":
                    status = result.RESULT_FALSE_TERMINATION
                elif result_str == "FALSE(valid-memcleanup)":
                    status = result.RESULT_FALSE_MEMCLEANUP
                else:
                    status = result.RESULT_FALSE_REACH
            else:
                status = result.RESULT_FALSE_REACH
        else:
            status = result.RESULT_UNKNOWN
        return status
