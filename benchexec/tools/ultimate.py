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
import os.path
import subprocess
import logging
import re

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
    
    SVCOMP17_WRAPPER_VERSIONS = {'f7c3ed31'}
    SVCOMP17_ULTIMATE_VERSIONS = {'0.0.1'}
    SVCOMP17_FORBIDDEN_FLAGS = {'--full-output','--architecture'}
    ULTIMATE_VERSION_REGEX = re.compile('^Version is (.*)$', re.MULTILINE)

    def executable(self):
        return util.find_executable('Ultimate.py')

    def version(self, executable):
        return self._version_from_tool(executable)

    def cmdline(self, executable, options, tasks, spec, rlimits):
        return self.determine_commandline_version(executable)(executable, options, tasks, spec, rlimits)
    
    def cmdline_svcomp17(self, executable, options, tasks, spec, rlimits):
        for flag in self.SVCOMP17_FORBIDDEN_FLAGS:
            if flag in options:
                options.remove(flag)

        return [executable] + [spec] + options + ['--full-output'] + tasks
    
    def cmdline_current(self, executable, options, tasks, spec, rlimits):
        if executable == None:
            raise Exception('No executable specified')

        cmdline = [executable]

        if spec != None:
            cmdline = cmdline + ['--spec'] + [spec]

        if tasks:
            cmdline = cmdline + ['--file'] + tasks

        if options:
            cmdline = cmdline + options

        return cmdline
    
    def determine_commandline_version(self, executable):
        bin_python_wrapper = [util.find_executable('Ultimate.py')]
        bin_ultimate = ['java', '-jar' , os.path.join(os.path.dirname(os.path.realpath(bin_python_wrapper[0])), 'plugins/org.eclipse.equinox.launcher_1.3.100.v20150511-1540.jar')]
        version_wrapper = self.get_version(bin_python_wrapper + ['--version'])
        version_ultimate = self.get_version(bin_ultimate + ['--version'])
        version_ultimate_match = self.ULTIMATE_VERSION_REGEX.search(version_ultimate)
        if not version_ultimate_match:
            raise RuntimeError('Could not obtain Ultimate version')

        version_ultimate = version_ultimate_match.group(1)
        
        msg = 'Detected Ultimate version {0} / {1}'.format(version_ultimate, version_wrapper)
        if version_wrapper in self.SVCOMP17_WRAPPER_VERSIONS and version_ultimate in self.SVCOMP17_ULTIMATE_VERSIONS:
            logging.info('{0}. Using SVCOMP17 compatibility mode'.format(msg))
            return self.cmdline_svcomp17
        else:
            logging.info(msg)
            return self.cmdline_current
    
    def get_version(self, command):
        try:
            process = subprocess.Popen(command,
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (stdout, stderr) = process.communicate()
        except OSError as e:
            logging.warning('Cannot run {0} to determine version: {1}'.
                            format(command, e.strerror))
            return ''
        if process.returncode:
            logging.warning('Cannot determine {0} version, exit code {1}'.
                            format(command, process.returncode))
            return ''
        return util.decode_to_string(stdout).strip()
    
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
