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
import logging
import os
import re
import subprocess

import benchexec.util as util
import benchexec.tools.template
import benchexec.result as result

_SVCOMP17_VERSIONS = {"f7c3ed31"}
_SVCOMP17_FORBIDDEN_FLAGS = {"--full-output", "--architecture"}
_ULTIMATE_VERSION_REGEX = re.compile('^Version is (.*)$', re.MULTILINE)
_LAUNCHER_JAR = "plugins/org.eclipse.equinox.launcher_1.3.100.v20150511-1540.jar"

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

    def _ultimate_version(self, executable):
        launcher_jar = os.path.join(os.path.dirname(executable), _LAUNCHER_JAR)
        if not os.path.isfile(launcher_jar):
            logging.warning('Cannot find {0} to determine Ultimate version'.
                            format(_LAUNCHER_JAR))
            return ''

        try:
            process = subprocess.Popen(["java", "-jar", launcher_jar, "--version"],
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (stdout, stderr) = process.communicate()
        except OSError as e:
            logging.warning('Cannot run Java to determine Ultimate version: {0}'.
                            format(e.strerror))
            return ''
        if stderr and not use_stderr:
            logging.warning('Cannot determine Ultimate version, error output: {0}'.
                            format(util.decode_to_string(stderr)))
            return ''
        if process.returncode:
            logging.warning('Cannot determine Ultimate version, exit code {0}'.
                            format(process.returncode))
            return ''

        version_ultimate_match = _ULTIMATE_VERSION_REGEX.search(util.decode_to_string(stdout))
        if not version_ultimate_match:
            logging.warning('Cannot determine Ultimate version, output: {0}'.
                            format(util.decode_to_string(stdout)))
            return ''

        return version_ultimate_match.group(1)

    @functools.lru_cache()
    def version(self, executable):
        wrapper_version = self._version_from_tool(executable)
        if wrapper_version in _SVCOMP17_VERSIONS:
            # Keep reported version number for old versions as they were before
            return wrapper_version

        ultimate_version = self._ultimate_version(executable)
        return ultimate_version + '-' + wrapper_version

    def _is_svcomp17_version(self, executable):
        return self.version(executable) in _SVCOMP17_VERSIONS

    def cmdline(self, executable, options, tasks, spec, rlimits):
        if self._is_svcomp17_version(executable):
            assert spec
            cmdline = [executable, spec]

            cmdline += [option for option in options if option not in _SVCOMP17_FORBIDDEN_FLAGS]

            cmdline.append("--full-output")

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
