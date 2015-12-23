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
import benchexec.util as Util
import benchexec.tools.template
import benchexec.result as result

class Tool(benchexec.tools.template.BaseTool):
    """
    This class serves as tool adaptor for Map2Check (https://github.com/hbgit/Map2Check)
    """

    REQUIRED_PATHS = [
                  "__init__.py",
                  "map2check.py",
                  "map2check-wrapper.sh",
                  "modules"
                  ]

    def executable(self):
        #Relative path to map2check wrapper
        return Util.find_executable('map2check-wrapper.sh')

    def program_files(self, executable):
        executableDir = os.path.dirname(executable)
        return [executableDir]

    def working_directory(self, executable):
        executableDir = os.path.dirname(executable)
        return executableDir

    def environment(self, executable):
        return {"additionalEnv" : {'PATH' :  ':.'}}

    def version(self, executable):
        return self._version_from_tool(executable)

    def name(self):
        return 'Map2Check'

    def cmdline(self, executable, options, sourcefiles, propertyfile, rlimits):
        assert len(sourcefiles) == 1, "only one sourcefile supported"
        assert propertyfile, "property file required"
        sourcefile = sourcefiles[0]
        return [executable] + options + ['-c', propertyfile, sourcefile]



    def determine_result(self, returncode, returnsignal, output, isTimeout):
        if not output:
            return result.RESULT_UNKNOWN
        output = output[-1].strip()
        status = result.RESULT_UNKNOWN

        if output.endswith('TRUE'):
            status = result.RESULT_TRUE_PROP
        elif 'FALSE' in output:
            if "FALSE(valid-memtrack)" in output:
                status = result.RESULT_FALSE_MEMTRACK
            elif "FALSE(valid-deref)" in output:
                status = result.RESULT_FALSE_DEREF
            elif "FALSE(valid-free)" in output:
                status = result.RESULT_FALSE_FREE
        elif output.endswith('UNKNOWN'):
            status = result.RESULT_UNKNOWN
        elif isTimeout:
            status = 'TIMEOUT'
        else:
            status = 'ERROR'

        return status
