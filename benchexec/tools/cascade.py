"""
Cascade Verification Tool
Copyright (c) 2015 New York University
All Rights Reserved

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

import benchexec.util as util
import benchexec.tools.template
import benchexec.result as result

class Tool(benchexec.tools.template.BaseTool):
    """
    Tool info for Cascade (http://cascade.cims.nyu.edu/).
    """

    REQUIRED_PATHS = [
                  "bin",
                  "cascade.sh",
                  "lib",
                  "run_cascade"
                  ]

    def executable(self):
        return util.find_executable('run_cascade')

    def name(self):
        return 'Cascade'

    def version(self, executable):
        return self._version_from_tool(executable)

    def cmdline(self, executable, options, tasks, propertyfile, rlimits):
        assert len(tasks) == 1, "only one sourcefile supported"
        inputfile = tasks[0]
        assert propertyfile is not None
        spec = ['-spec', propertyfile]
        return [executable] + options + spec + [inputfile]

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        output = '\n'.join(output)
        if "FALSE" in output:
            if "FALSE(valid-deref)" in output:
                status = result.RESULT_FALSE_DEREF
            elif "FALSE(valid-free)" in output:
                status = result.RESULT_FALSE_FREE
            elif "FALSE(valid-memtrack)" in output:
                status = result.RESULT_FALSE_MEMTRACK
            else:
                status = result.RESULT_FALSE_REACH
        elif "TRUE" in output:
            status = result.RESULT_TRUE_PROP
        else:
            status = result.RESULT_UNKNOWN

        return status
