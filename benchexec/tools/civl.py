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

import benchexec.util as util
import benchexec.tools.template
import benchexec.result as result

class Tool(benchexec.tools.template.BaseTool):

    REQUIRED_PATHS = [
                  "civl",
                  "lib",
                  "provers"
                  ]

    def executable(self):
        return util.find_executable('civl')

    def name(self):
        return 'CIVL'

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        if any('__VERIFIER_error() is called.' in s for s in output):
            status = result.RESULT_FALSE_REACH
        elif any('The standard properties hold for all executions.' in s for s in output):
            status = result.RESULT_TRUE_PROP
        else:
            status = result.RESULT_UNKNOWN

        return status
