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

class Tool(benchexec.tools.template.BaseTool):

    def executable(self):
        return util.find_executable('ufo.sh')


    def name(self):
        return 'Ufo'


    def determine_result(self, returncode, returnsignal, output, isTimeout):
        output = '\n'.join(output)
        if returnsignal == 9 or returnsignal == (128+9):
            if isTimeout:
                status = "TIMEOUT"
            else:
                status = "KILLED BY SIGNAL 9"
        elif returncode == 1 and "program correct: ERROR unreachable" in output:
            status = "SAFE"
        elif returncode != 0:
            status = "ERROR ({0})".format(returncode)
        elif "ERROR reachable" in output:
            status = "UNSAFE"
        elif "program correct: ERROR unreachable" in output:
            status = "SAFE"
        else:
            status = "FAILURE"
        return status