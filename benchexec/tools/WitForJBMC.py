"""
BenchExec is a framework for reliable benchmarking.
This file is part of BenchExec.
Copyright (C) 2007-2021  Dirk Beyer
All rights reserved.
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at
    http://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import benchexec.tools.template
import benchexec.result as result


class Tool(benchexec.tools.template.BaseTool2):

    """
    Tool info for Wit4JBMC
    (https://github.com/Anthonysdu/MSc-project/blob/main/jbmc/Wit4JBMC.py).
    """
    
    def executable(self, tool_locator):
        return tool_locator.find_executable("Wit4JBMC.py")

    def version(self, executable):
        return self._version_from_tool(executable)

    def name(self):
        return "Wit4JBMC"

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
                break
            else:
                validation = "true"

        if validation == "false":
            status = result.RESULT_FALSE_PROP
        # print(exit_code)
        elif validation == "true":
            status = result.RESULT_TRUE_PROP

        elif validation == "unknown":
            status = result.RESULT_UNKNOWN
        else:
            status = result.RESULT_ERROR
        return status
