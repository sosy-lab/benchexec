# coding=utf-8
"""
Copyright (c) 2015 Guang Chen

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
from benchexec import util, result
from benchexec.tools.template import BaseTool

__author__ = 'guangchen'


class Tool(BaseTool):

    REQUIRED_PATHS = [
                  "absref.sh",
                  "beagle-ir2elts",
                  "llvm-dis",
                  "llvm-lit",
                  "llvm-tblgen",
                  "opt",
                  "sv_absref"
                  ]

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        if isTimeout:
            return 'TIMEOUT'
        if returncode != 0:
            return 'CRASH'
        output = str(output)
        if 'TRUE' in output:
            return result.RESULT_TRUE_PROP
        if 'FALSE' in output and 'bb_VERIFY_ERROR' in output:
            return result.RESULT_FALSE_REACH
        return result.RESULT_UNKNOWN

    def name(self):
        return 'Ceagle AbsRef'

    def version(self, executable):
        return self._version_from_tool(executable)

    def executable(self):
        return util.find_executable('absref.sh')

