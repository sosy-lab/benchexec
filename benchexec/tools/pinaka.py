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

    REQUIRED_PATHS = ["pinaka-wrapper.sh", "pinaka"]

    def executable(self, tool_locator):
        return tool_locator.find_executable("pinaka-wrapper.sh")

    def version(self, executable):
        return self._version_from_tool(executable)

    def name(self):
        return "Pinaka"

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
        output = run.output._lines
        status = ""

        if returnsignal == 0 and ((returncode == 0) or (returncode == 10)):
            if "VERIFICATION FAILED (ReachSafety)\n" in output:
                status = result.RESULT_FALSE_REACH
            elif "VERIFICATION FAILED (NoOverflow)\n" in output:
                status = result.RESULT_FALSE_OVERFLOW
            elif "VERIFICATION SUCCESSFUL\n" in output:
                status = result.RESULT_TRUE_PROP
            else:
                status = result.RESULT_UNKNOWN
        else:
            status = result.RESULT_ERROR

        return status
