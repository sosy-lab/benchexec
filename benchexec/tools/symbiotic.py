"""
BenchExec is a framework for reliable benchmarking.
This file is part of BenchExec.

Copyright (C) 2007-2015  Dirk Beyer
Copyright (C) 2016-2017  Marek Chalupa

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
from os.path import dirname
from os.path import join as joinpath

import benchexec.util as util
import benchexec.tools.template
import benchexec.result as result

from . symbiotic4 import Tool as OldSymbiotic

class Tool(OldSymbiotic):
    """
    Symbiotic tool info object
    """

    REQUIRED_PATHS_4_0_1 = [
                  "bin",
                  "include",
                  "lib",
                  "lib32",
                  "llvm-3.8.1",
                  ]

    REQUIRED_PATHS_5_0_0 = [
                  "bin",
                  "include",
                  "lib",
                  "lib32",
                  "llvm-3.9.1",
                  ]

    def executable(self):
        """
        Find the path to the executable file that will get executed.
        This method always needs to be overridden,
        and most implementations will look similar to this one.
        The path returned should be relative to the current directory.
        """
        exe = util.find_executable('bin/symbiotic', exitOnError=False)
        if exe:
            return exe
        else:
            # this may be the old version of Symbiotic
            return OldSymbiotic.executable(self)

    def program_files(self, executable):
        installDir = joinpath(dirname(executable), '..')
        if self._version_newer_than('5.0.0'):
            paths = self.REQUIRED_PATHS_5_0_0
        elif self._version_newer_than('4.0.1'):
            paths = self.REQUIRED_PATHS_4_0_1
        else:
            paths = OldSymbiotic.REQUIRED_PATHS

        return [executable] + util.flatten(util.expand_filename_pattern(path, installDir) for path in paths)

    def _version_newer_than(self, vers):
        """
        Determine whether the version is greater than some given version
        """
        v = self.version(self.executable())
        vers_num = v[:v.index('-')]
        if not vers_num[0].isdigit():
            # this is the old version which is "older" than any given version
            return False

        v1 = list(map(int, vers_num.split('.')))
        v2 = list(map(int, vers.split('.')))
        assert len(v1) == 3
        assert len(v2) == 3

        if v1[0] > v2[0]:
            return True
        elif v1[0] == v2[0]:
            if v1[1] == v2[1]:
                return v1[2] >= v2[2]
            elif v1[1] > v2[1]:
                return True

        return False

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        if isTimeout:
            return 'timeout'

        if output is None:
            return 'error (no output)'

        if self._version_newer_than('4.0.1'):
            for line in output:
              line = line.strip()
              if line == 'RESULT: true':
                return result.RESULT_TRUE_PROP
              elif line == 'RESULT: unknown':
                return result.RESULT_UNKNOWN
              elif line.startswith('RESULT: false(valid-deref)'):
                return result.RESULT_FALSE_DEREF
              elif line.startswith('RESULT: false(valid-free)'):
                return result.RESULT_FALSE_FREE
              elif line.startswith('RESULT: false(valid-memtrack)'):
                return result.RESULT_FALSE_MEMTRACK
              elif line.startswith('RESULT: false(no-overflow)'):
                return result.RESULT_FALSE_OVERFLOW
              elif line.startswith('RESULT: false'):
                return result.RESULT_FALSE_REACH
        else:
            # old version of Symbiotic
            return OldSymbiotic.determine_result(self, returncode, returnsignal, output, isTimeout)

        return result.RESULT_ERROR

