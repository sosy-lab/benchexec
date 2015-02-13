#!/usr/bin/env python

"""
CPAchecker is a tool for configurable software verification.
This file is part of CPAchecker.

Copyright (C) 2007-2014  Dirk Beyer
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


CPAchecker web page:
  http://cpachecker.sosy-lab.org
"""

# prepare for Python 3
from __future__ import absolute_import, division, print_function, unicode_literals

import logging
import subprocess
import sys
import string
import os
import re

sys.dont_write_bytecode = True # prevent creation of .pyc files

if __name__ == "__main__":
    sys.path.append(os.path.join(os.path.dirname(__file__), os.path.pardir, os.path.pardir))

import benchexec.result as result
import benchexec.util as util
import benchexec.tools.template
from benchexec.model import SOFTTIMELIMIT

REQUIRED_PATHS = [
                  "lib/java/runtime",
                  "lib/*.jar",
                  "lib/native/x86_64-linux",
                  "scripts",
                  "cpachecker.jar",
                  "config",
                  ]

class Tool(benchexec.tools.template.BaseTool):
    """
    Tool wrapper for CPAchecker.
    It has additional features such as building CPAchecker before running it
    if executed within a source checkout.
    It also supports extracting data from the statistics output of CPAchecker
    for adding it to the result tables.
    """

    def executable(self):
        executable = util.find_executable('cpa.sh', 'scripts/cpa.sh')
        executableDir = os.path.join(os.path.dirname(executable), os.path.pardir)
        if os.path.isdir(os.path.join(executableDir, 'src')):
            self._buildCPAchecker(executableDir)
        if not os.path.isfile(os.path.join(executableDir, "cpachecker.jar")):
            logging.warning("Required JAR file for CPAchecker not found in {0}.".format(executableDir))
        return executable


    def _buildCPAchecker(self, executableDir):
        logging.debug('Building CPAchecker in directory {0}.'.format(executableDir))
        ant = subprocess.Popen(['ant', '-lib', 'lib/java/build', '-q', 'jar'], cwd=executableDir, shell=util.is_windows())
        (stdout, stderr) = ant.communicate()
        if ant.returncode:
            sys.exit('Failed to build CPAchecker, please fix the build first.')


    def program_files(self, executable):
        executableDir = os.path.join(os.path.dirname(executable), os.path.pardir)
        return util.flatten(util.expand_filename_pattern(path, executableDir) for path in REQUIRED_PATHS)


    def working_directory(self, executable):
        return os.curdir


    def version(self, executable):
        try:
            process = subprocess.Popen([executable, '-help'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (stdout, stderr) = process.communicate()
        except OSError as e:
            logging.warning('Cannot run CPAchecker to determine version: {0}'.format(e.strerror))
            return ''
        if stderr:
            logging.warning('Cannot determine CPAchecker version, error output: {0}'.format(util.decode_to_string(stderr)))
            return ''
        if process.returncode:
            logging.warning('Cannot determine CPAchecker version, exit code {0}'.format(process.returncode))
            return ''
        stdout = util.decode_to_string(stdout)
        line = next(l for l in stdout.splitlines() if l.startswith('CPAchecker'))
        line = line.replace('CPAchecker' , '')
        line = line.split('(')[0]
        return line.strip()

    def name(self):
        return 'CPAchecker'


    def cmdline(self, executable, options, sourcefiles, propertyfile=None, rlimits={}):
        if SOFTTIMELIMIT in rlimits:
            if "-timelimit" in options:
                logging.warning('Time limit already specified in command-line options, not adding time limit from benchmark definition to the command line.')
            else:
                options = options + ["-timelimit", str(rlimits[SOFTTIMELIMIT]) + "s"] # benchmark-xml uses seconds as unit

        # if data.MEMLIMIT in rlimits:
        #     if "-heap" not in options:
        #         heapsize = rlimits[MEMLIMIT]*0.8 # 20% overhead for non-java-memory
        #         options = options + ["-heap", str(int(heapsize)) + "MiB"] # benchmark-xml uses MiB as unit

        if ("-stats" not in options):
            options = options + ["-stats"]

        spec = ["-spec", propertyfile] if propertyfile is not None else []
        return [executable] + options + spec + sourcefiles


    def determine_result(self, returncode, returnsignal, output, isTimeout):
        """
        @param returncode: code returned by CPAchecker
        @param returnsignal: signal, which terminated CPAchecker
        @param output: the output of CPAchecker
        @return: status of CPAchecker after executing a run
        """

        def isOutOfNativeMemory(line):
            return ('std::bad_alloc'             in line # C++ out of memory exception (MathSAT)
                 or 'Cannot allocate memory'     in line
                 or 'Native memory allocation (malloc) failed to allocate' in line # JNI
                 or line.startswith('out of memory')     # CuDD
                 )

        if returnsignal == 0 and returncode > 128:
            # shells sets return code to 128+signal when a signal is received
            returnsignal = returncode - 128

        if returnsignal != 0:
            if returnsignal == 6:
                status = 'ABORTED'
            elif returnsignal == 9 and isTimeout:
                status = 'TIMEOUT'
            elif returnsignal == 11:
                status = 'SEGMENTATION FAULT'
            elif returnsignal == 15:
                status = 'KILLED'
            else:
                status = 'KILLED BY SIGNAL '+str(returnsignal)

        elif returncode != 0:
            status = 'ERROR ({0})'.format(returncode)

        else:
            status = ''

        for line in output:
            if 'java.lang.OutOfMemoryError' in line:
                status = 'OUT OF JAVA MEMORY'
            elif isOutOfNativeMemory(line):
                status = 'OUT OF NATIVE MEMORY'
            elif 'There is insufficient memory for the Java Runtime Environment to continue.' in line \
                    or 'cannot allocate memory for thread-local data: ABORT' in line:
                status = 'OUT OF MEMORY'
            elif 'SIGSEGV' in line:
                status = 'SEGMENTATION FAULT'
            elif ((returncode == 0 or returncode == 1)
                    and ('Exception' in line or 'java.lang.AssertionError' in line)
                    and not line.startswith('cbmc')): # ignore "cbmc error output: ... Minisat::OutOfMemoryException"
                status = 'ASSERTION' if 'java.lang.AssertionError' in line else 'EXCEPTION'
            elif 'Could not reserve enough space for object heap' in line:
                status = 'JAVA HEAP ERROR'
            elif line.startswith('Error: ') and not status:
                status = 'ERROR'
                if 'Unsupported C feature (recursion)' in line:
                    status = 'ERROR (recursion)'
                elif 'Unsupported C feature (threads)' in line:
                    status = 'ERROR (threads)'
                elif 'Parsing failed' in line:
                    status = 'ERROR (parsing failed)'
            elif line.startswith('For your information: CPAchecker is currently hanging at') and status == 'ERROR (1)' and isTimeout:
                status = 'TIMEOUT'

            elif line.startswith('Verification result: '):
                line = line[21:].strip()
                if line.startswith('TRUE'):
                    newStatus = result.STATUS_TRUE_PROP
                elif line.startswith('FALSE'):
                    newStatus = result.STATUS_FALSE_REACH
                    match = re.match('.* Property violation \(([^:]*)(:.*)?\) found by chosen configuration.*', line)
                    if match and match.group(1) in ['valid-deref', 'valid-free', 'valid-memtrack']:
                        newStatus = result.STR_FALSE + '(' + match.group(1) + ')'
                else:
                    newStatus = result.STATUS_UNKNOWN

                if not status:
                    status = newStatus
                elif newStatus != result.STATUS_UNKNOWN:
                    status = "{0} ({1})".format(status, newStatus)

        if not status:
            status = result.STATUS_UNKNOWN
        return status


    def add_column_values(self, output, columns):
        for column in columns:

            # search for the text in output and get its value,
            # stop after the first line, that contains the searched text
            column.value = "-" # default value
            for line in output:
                if column.text in line:
                    startPosition = line.find(':') + 1
                    endPosition = line.find('(', startPosition) # bracket maybe not found -> (-1)
                    if (endPosition == -1):
                        column.value = line[startPosition:].strip()
                    else:
                        column.value = line[startPosition: endPosition].strip()
                    break


if __name__ == "__main__":
    tool = Tool()
    executable = tool.executable()
    print('Executable: {0}'.format(os.path.abspath(executable)))
    print('Version: {0}'.format(tool.version(executable)))
