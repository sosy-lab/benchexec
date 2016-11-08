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

import benchexec.util as util
import benchexec.tools.template
import benchexec.result as result

class UltimateTool(benchexec.tools.template.BaseTool):
    """
    Abstract tool info for Ultimate-based tools.
    """

    def executable(self):
        return util.find_executable('Ultimate.py')

    def version(self, executable):
        return self._version_from_tool(executable)

    def cmdline(self, executable, options, tasks, spec, rlimits):
        # search for witness in options and put it at the end / together with tasks
        for option in options:
            if option.endswith('.graphml'):
                options.remove(option)
                return [executable] + [spec] + options + ['--full-output'] + tasks + [option]
        return [executable] + [spec] + options + ['--full-output'] + tasks

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        if (returnsignal == 9):
            return 'TIMEOUT'

        status = result.RESULT_UNKNOWN
        for line in output:
            if line.startswith('FALSE(valid-free)'):
                status = result.RESULT_FALSE_FREE
                break
            elif line.startswith('FALSE(valid-deref)'):
                status = result.RESULT_FALSE_DEREF
                break
            elif line.startswith('FALSE(valid-memtrack)'):
                status = result.RESULT_FALSE_MEMTRACK
                break
            elif line.startswith('FALSE(TERM)'):
                status = result.RESULT_FALSE_TERMINATION
                break
            elif line.startswith('FALSE(OVERFLOW)'):
                status = result.RESULT_FALSE_OVERFLOW
                break
            elif line.startswith('FALSE'):
                status = result.RESULT_FALSE_REACH
                break
            elif line.startswith('TRUE'):
                status = result.RESULT_TRUE_PROP
                break
            elif line.startswith('UNKNOWN'):
                status = result.RESULT_UNKNOWN
                break
            elif line.startswith('ERROR'):
                status = 'ERROR'
                break

        return status

    def get_value_from_output(self, lines, identifier):
        # search for the text in output and get its value,
        # stop after the first line, that contains the searched text
        for line in lines:
            if identifier in line:
                startPosition = line.find('=') + 1
                return line[startPosition:].strip()
        return None
