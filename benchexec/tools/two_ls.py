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
    """
    Wrapper for 2LS (http://www.cprover.org/2LS).
    """

    def executable(self):
        return util.find_executable('2ls')

    def name(self):
        return '2LS'

    def version(self, executable):
        return self._version_from_tool(executable)

    """
      We ignore the property file because we currently only support
        CHECK( init(main()), LTL(G ! call(__VERIFIER_error())) )
    """
    def cmdline(self, executable, options, tasks, propertyfile, rlimits):
        return [executable] + options + tasks

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        output = '\n'.join(output)
        if ((returnsignal == 9) or (returnsignal == 15)) and isTimeout:
            status = 'TIMEOUT'
        elif returnsignal == 9:
            status = "KILLED BY SIGNAL 9"
        elif returnsignal != 0:
            status = "ERROR(SIGNAL "+str(returnsignal)+")"
        elif returncode == 0:
            status = result.RESULT_TRUE_PROP
        elif returncode == 10:
            status = result.RESULT_FALSE_REACH
        else:
            status = result.RESULT_UNKNOWN
        return status


