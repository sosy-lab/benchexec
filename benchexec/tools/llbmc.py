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
import subprocess

import benchexec.util as util
import benchexec.tools.template
import benchexec.result as result

class Tool(benchexec.tools.template.BaseTool):
    """
    This class serves as tool adaptor for LLBMC
    """

    def executable(self):
        return util.find_executable('llbmc')


    def version(self, executable):
        return self._version_from_tool(executable).splitlines()[2][8:18]


    def name(self):
        return 'LLBMC'


    def cmdline(self, executable, options, tasks, propertyfile, rlimits):
        assert len(tasks) == 1, "only one inputfile supported"
        inputfile = tasks[0]
        # compile inputfile with clang
        self.prepInputfile = self._prepareInputfile(inputfile)

        return [executable] + options + [self.prepInputfile]


    def _prepareInputfile(self, inputfile):
        clangExecutable = util.find_executable('clang')
        newFilename     = inputfile + ".o"

        subprocess.Popen([clangExecutable,
                            '-c',
                            '-emit-llvm',
                            '-std=gnu89',
                            '-m32',
                            inputfile,
                            '-O0',
                            '-o',
                            newFilename,
                            '-w'],
                          stdout=subprocess.PIPE).wait()

        return newFilename


    def determine_result(self, returncode, returnsignal, output, isTimeout):
        status = result.RESULT_UNKNOWN

        for line in output:
            if 'Error detected.' in line:
                status = result.RESULT_FALSE_REACH
            elif 'No error detected.' in line:
                status = result.RESULT_TRUE_PROP

        # delete tmp-files
        try:
            os.remove(self.prepInputfile)
        except OSError:
            print("Could not remove file " + self.prepInputfile + "! Maybe clang call failed")

        return status
