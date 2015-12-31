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

import subprocess
import os
import benchexec.util as Util
import benchexec.tools.template
import benchexec.result as result


class Tool(benchexec.tools.template.BaseTool):

    """
    This class serves as tool adaptor for DepthK (www.esbmc.org)
    Autor: Williame Rocha - williame.rocha10@gmail.com - Federal University of Amazonas, Brazil.
    """

    REQUIRED_PATHS = [
                  "depthk.py",
                  "depthk-wrapper.sh",
                  "esbmc",
                  "__init__.py",
                  "modules",
                  "tokenizer"
                  ]

    def executable(self):

        # Relative path to depthk wrapper

        return Util.find_executable('depthk-wrapper.sh')

    def working_directory(self, executable):
        executableDir = os.path.dirname(executable)
        return executableDir

    def environment(self, executable):
        return {'additionalEnv': {'PATH': ':.'}}

    def version(self, executable):
        workingDir = self.working_directory(executable)

        version = subprocess.Popen([workingDir + '/depthk.py',
                                   '--version'],
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout.readline().decode()
        return version

    def name(self):
        return 'DepthK'

    def cmdline(
        self,
        executable,
        options,
        tasks,
        propertyfile,
        rlimits,
        ):

        assert len(tasks) == 1, 'only one sourcefile supported'
        assert propertyfile, 'property file required'
        sourcefile = tasks[0]
        return [executable] + options + ['-c', propertyfile, sourcefile]

    def determine_result(
        self,
        returncode,
        returnsignal,
        output,
        isTimeout,
        ):

        if len(output) <= 0:
            return result.RESULT_ERROR

        output = output[-1].strip()

        if 'TRUE' in output:
            return result.RESULT_TRUE_PROP
        elif 'FALSE' in output:
            if 'FALSE(valid-memtrack)' in output:
                return result.RESULT_FALSE_MEMTRACK
            elif 'FALSE(valid-deref)' in output:
                return result.RESULT_FALSE_DEREF
            elif 'FALSE(no-overflow)' in output:
                return result.RESULT_FALSE_OVERFLOW
            else:
                return result.RESULT_FALSE_REACH
        elif 'UNKNOWN' in output:
            return result.RESULT_UNKNOWN

        return result.RESULT_ERROR
