"""
BenchExec is a framework for reliable benchmarking.
This file is part of BenchExec.

Copyright (C) 2015  Daniel Dietsch
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

import functools
import os

import benchexec.util as util
import benchexec.tools.template
import benchexec.result as result

_SVCOMP17_VERSIONS = {"f7c3ed31"}
_SVCOMP17_FORBIDDEN_FLAGS = {"--full-output", "--architecture"}

class UltimateTool(benchexec.tools.template.BaseTool):
    """
    Abstract tool info for Ultimate-based tools.
    """

    REQUIRED_PATHS = [
              "artifacts.xml",
              "config",
              "configuration",
              "data",
              "features",
              "p2",
              "plugins",
              "LICENSE",
              "LICENSE.GPL",
              "LICENSE.GPL.LESSER",
              "README",
              "Ultimate",
              "Ultimate.ini",
              "Ultimate.py",
              "z3",
              "mathsat",
              "cvc4",
              ]

    def executable(self):
        return util.find_executable('Ultimate.py')

    @functools.lru_cache()
    def version(self, executable):
        # Would be good if this method could get the real Ultimate version
        # number, too, not only the git hash.
        return self._version_from_tool(executable)

    def _is_svcomp17_version(self, executable):
        return self.version(executable) in _SVCOMP17_VERSIONS

    def cmdline(self, executable, options, tasks, spec, rlimits):
        if self._is_svcomp17_version(executable):
            assert spec
            cmdline = [executable, spec]

            cmdline += [option for option in options if option not in _SVCOMP17_FORBIDDEN_FLAGS]

            cmdlinea.append("--full-output")

            cmdline += tasks
            return cmdline
        else:
            cmdline = [executable]

            if spec:
                cmdline += ['--spec', spec]

            if tasks:
                cmdline += ['--file'] + tasks

            # Not sure if we should append --full-output for new Ultimate, too

            cmdline += options
            return cmdline

    def program_files(self, executable):
        installDir = os.path.dirname(executable)
        paths = self.REQUIRED_PATHS_SVCOMP17 if self._is_svcomp17_version(executable) else self.REQUIRED_PATHS
        return [executable] + util.flatten(util.expand_filename_pattern(path, installDir) for path in paths)

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        for line in output:
            if line.startswith('FALSE(valid-free)'):
                return result.RESULT_FALSE_FREE
            elif line.startswith('FALSE(valid-deref)'):
                return result.RESULT_FALSE_DEREF
            elif line.startswith('FALSE(valid-memtrack)'):
                return result.RESULT_FALSE_MEMTRACK
            elif line.startswith('FALSE(TERM)'):
                return result.RESULT_FALSE_TERMINATION
            elif line.startswith('FALSE(OVERFLOW)'):
                return result.RESULT_FALSE_OVERFLOW
            elif line.startswith('FALSE'):
                return result.RESULT_FALSE_REACH
            elif line.startswith('TRUE'):
                return result.RESULT_TRUE_PROP
            elif line.startswith('UNKNOWN'):
                return result.RESULT_UNKNOWN
            elif line.startswith('ERROR'):
                status = result.RESULT_ERROR
                if line.startswith('ERROR: INVALID WITNESS FILE'):
                    status += ' (invalid witness file)'
                return status
        return result.RESULT_UNKNOWN

    def get_value_from_output(self, lines, identifier):
        # search for the text in output and get its value,
        # stop after the first line, that contains the searched text
        for line in lines:
            if identifier in line:
                startPosition = line.find('=') + 1
                return line[startPosition:].strip()
        return None
