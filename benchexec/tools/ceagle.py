"""
BenchExec is a framework for reliable benchmarking.
This file is part of BenchExec.

Copyright (C) 2007-2015  Dirk Beyer
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

import benchexec.result as result
import benchexec.util as util
import benchexec.tools.template

class Tool(benchexec.tools.template.BaseTool):

    REQUIRED_PATHS = [
                  "ceagle.sh",
                  "dfs.py",
                  "parse2str.py",
                  "parsece.sh",
                  "svcore",
                  "svie",
                  "verifier.py",
                  "z3"
                  ]

    def executable(self):
        return util.find_executable('ceagle.sh')

    def version(self, executable):
        return self._version_from_tool(executable)

    def name(self):
        return 'Ceagle'

    def cmdline(self, executable, options, tasks, propertyfile, rlimits):
        return [executable] + options + tasks

    def determine_result(self, returncode, returnsignal, output, isTimeout):

        status = result.RESULT_UNKNOWN
        stroutput = str(output)

        if isTimeout:
            status = 'TIMEOUT'
        elif 'TRUE' in stroutput:
            status = result.RESULT_TRUE_PROP
        elif 'FALSE' in stroutput:
            status = result.RESULT_FALSE_REACH
        elif 'UNKNOWN' in stroutput:
            status = result.RESULT_UNKNOWN
        else:
            status = result.RESULT_UNKNOWN

        return status
