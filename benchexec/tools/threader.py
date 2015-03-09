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

import os
import benchexec.util as util
import benchexec.tools.template
import benchexec.result as result

class Tool(benchexec.tools.template.BaseTool):
    """
    This class serves as tool adaptor for Threader (http://www.esbmc.org/)
    """

    def executable(self):
        return util.find_executable('threader.sh')


    def program_files(self, executable):
        executableDir = os.path.dirname(executable)
        return [executableDir]


    def working_directory(self, executable):
        executableDir = os.path.dirname(executable)
        return executableDir


    def environment(self, executable):
        return {"additionalEnv" : {'PATH' :  ':.'}}


    def version(self, executable):
        return self._version_from_tool('cream', '--help').splitlines()[2][34:42]


    def name(self):
        return 'Threader'


    def cmdline(self, executable, options, tasks, propertyfile, rlimits):
        assert len(tasks) == 1, "only one inputfile supported"
        inputfile = tasks[0]
        return [executable] + options + [inputfile]


    def determine_result(self, returncode, returnsignal, output, isTimeout):
        output = '\n'.join(output)
        if 'SSSAFE' in output:
            status = result.RESULT_TRUE_PROP
        elif 'UNSAFE' in output:
            status = result.RESULT_FALSE_REACH
        else:
            status = result.RESULT_UNKNOWN

        if status == result.RESULT_UNKNOWN and isTimeout:
            status = 'TIMEOUT'

        return status
