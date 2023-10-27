# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.tools.template
import benchexec.result as result
from benchexec.tools.template import ToolNotFoundException


class Tool(benchexec.tools.template.BaseTool2):

    """
    Tool info for jcwit
    (https://github.com/Chriszai/JCWIT).
    """

    def executable(self, tool_locator):
        return tool_locator.find_executable("jcwit.py")

    def version(self, executable):
        return self._version_from_tool(executable)

    def name(self):
        return "jcwit"

    def cmdline(self, executable, options, task, rlimits):
        return [executable] + options + list(task.input_files)

    def determine_result(self, run):
        output = run.output
        validation = "unknown"
        for line in output:
            if "Exception" in line:
                if "AssertionError" in line:
                    validation = "false"
                else:
                    validation = "unknown"
                    
            if "Witness result: Unknown" in line:
                validation = "unknown"
                break
            elif "Witness result: False" in line:
                validation = "false"
                break
            else:
                if "Witness validation: False" in line:
                    validation = "false"
                    break
                elif "Witness validation: Unknown":
                    validation = "unknown"
                    break
                else:
                    validation = "true"

        if validation == "false":
            status = result.RESULT_FALSE_PROP

        elif validation == "true":
            status = result.RESULT_TRUE_PROP

        elif validation == "unknown":
            status = result.RESULT_UNKNOWN
        else:
            status = result.RESULT_ERROR
        return status
        