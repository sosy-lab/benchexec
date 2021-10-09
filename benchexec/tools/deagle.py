# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.result as result
import benchexec.util as util
import benchexec.tools.template


class Tool(benchexec.tools.template.BaseTool2):
    def executable(self, tool_locator):
        return tool_locator.find_executable("deagle")

    def name(self):
        return "Deagle"

    def version(self, executable):
        return self._version_from_tool(executable)

    def get_data_model(self, task):
        if isinstance(task.options, dict) and task.options.get("language") == "C":
            data_model = task.options.get("data_model")
            if data_model == "LP64":
                return ["--64"]
        return ["--32"] # default

    def cmdline(self, executable, options, task, rlimits):
        return [executable] + options + self.get_data_model(task) + list(task.input_files_or_identifier)

    def determine_result(self, run):
        status = result.RESULT_UNKNOWN

        output = run.output
        stroutput = str(output)

        if "SUCCESSFUL" in stroutput:
            status = result.RESULT_TRUE_PROP
        elif "FAILED" in stroutput:
            status = result.RESULT_FALSE_REACH
        else:
            status = result.RESULT_UNKNOWN

        return status
