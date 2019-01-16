"""
BenchExec is a framework for reliable benchmarking.
This file is part of BenchExec.

Copyright (C) 2007-2015  Dirk Beyer
Copyright (C) 2016-2018  Marek Chalupa

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

    REQUIRED_PATHS_6_0_0 = [
                  "bin",
                  "include",
                  "properties",
                  "lib",
                  "llvm-4.0.1",
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
        if self._version_newer_than('6.0.0'):
            paths = self.REQUIRED_PATHS_6_0_0
        elif self._version_newer_than('5.0.0'):
            paths = self.REQUIRED_PATHS_5_0_0
        elif self._version_newer_than('4.0.1'):
            paths = self.REQUIRED_PATHS_4_0_1
        else:
            paths = OldSymbiotic.REQUIRED_PATHS

        return [executable] + self._program_files_from_executable(executable, paths, parent_dir=True)

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

    def _getPhase(self, output):
        lastphase = 'before-instr'
        for line in output:
            if line.startswith('INFO: Starting instrumentation'):
                lastphase='instrumentation'
            elif line.startswith('INFO: Instrumentation time'):
                lastphase='instr-finished'
            elif line.startswith('INFO: Starting slicing'):
                lastphase='slicing'
            elif line.startswith('INFO: Total slicing time'):
                lastphase='slicing-finished'
            elif line.startswith('INFO: Starting verification'):
                lastphase='verification'
            elif line.startswith('INFO: Verification time'):
                lastphase='verification-finished'
            elif line.startswith('INFO: Replaying error path'):
                lastphase='cex-confirmation'
            elif line.startswith('INFO: Replaying error path time'):
                lastphase='cex-confirmation-finished'

        return lastphase

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        if output is None:
            return '{0}(no output)'.format(result.RESULT_ERROR)

        if self._version_newer_than('4.0.1'):
            for line in output:
              line = line.strip()
              if line == 'RESULT: true':
                return result.RESULT_TRUE_PROP
              elif line == 'RESULT: unknown':
                return result.RESULT_UNKNOWN
              elif line == 'RESULT: done':
                return result.RESULT_DONE
              elif line.startswith('RESULT: false(valid-deref)'):
                return result.RESULT_FALSE_DEREF
              elif line.startswith('RESULT: false(valid-free)'):
                return result.RESULT_FALSE_FREE
              elif line.startswith('RESULT: false(valid-memtrack)'):
                return result.RESULT_FALSE_MEMTRACK
              elif line.startswith('RESULT: false(valid-memcleanup)'):
                return result.RESULT_FALSE_MEMCLEANUP
              elif line.startswith('RESULT: false(no-overflow)'):
                return result.RESULT_FALSE_OVERFLOW
              elif line.startswith('RESULT: false(termination)'):
                return result.RESULT_FALSE_TERMINATION
              elif line.startswith('RESULT: false'):
                return result.RESULT_FALSE_REACH
        else:
            # old version of Symbiotic
            return OldSymbiotic.determine_result(self, returncode, returnsignal, output, isTimeout)

        if isTimeout:
            return self._getPhase(output) # generates TIMEOUT(phase)
        elif returnsignal != 0:
            return 'KILLED (signal {0}, {1})'.format(returnsignal, self._getPhase(output))
        elif returncode != 0:
            return '{0}(returned {1}, {2})'.format(result.RESULT_ERROR, returncode, self._getPhase(output))

        return '{0}(unknown, {1})'.format(result.RESULT_ERROR, self._getPhase(output))

