"""
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
                  "clang-3.7",
                  "libLLVM-3.7.so.1",
                  "opt-3.7",
                  "skink.sh",
                  "skink-v1.0.jar",
                  "test.sh",
                  "z3"
                  ]

    def executable(self):
        return util.find_executable('skink.sh')

    def name(self):
        return 'skink'

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        output = '\n'.join(output)
        if "TRUE" in output:
            status = result.RESULT_TRUE_PROP
        elif "FALSE" in output:
            status = result.RESULT_FALSE_REACH
        else:
            status = result.RESULT_UNKNOWN
        return status
