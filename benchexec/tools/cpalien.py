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
# prepare for Python 3
from __future__ import absolute_import, division, print_function, unicode_literals

import sys
import os
import re
import benchexec.result as result

sys.dont_write_bytecode = True # prevent creation of .pyc files

if __name__ == "__main__":
    sys.path.append(os.path.join(os.path.dirname(__file__), os.path.pardir, os.path.pardir))

import benchexec.tools.cpachecker

class Tool(benchexec.tools.cpachecker.Tool):

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

        undef = False
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
            elif line.startswith('Error: ') and not status.startswith('ERROR'):
                status = 'ERROR'
                if 'Unsupported C feature (recursion)' in line:
                    status = 'ERROR (recursion)'
                elif 'Unsupported C feature (threads)' in line:
                    status = 'ERROR (threads)'
                elif 'Parsing failed' in line:
                    status = 'ERROR (parsing failed)'
                elif 'Unknown function' in line:
                    status = 'ERROR (unknown function)'
            elif line.startswith("Non-target undefined behavior detected."):
                status = "ERROR (undefined behavior)"
                undef = True;

            elif line.startswith('Verification result: '):
                line = line[21:].strip()
                if line.startswith('TRUE'):
                    newStatus = result.RESULT_TRUE_PROP
                elif line.startswith('FALSE'):
                    newStatus = result.RESULT_FALSE_REACH
                    match = re.match('.* Property violation \(([^:]*)(:.*)?\) found by chosen configuration.*', line)
                    if match and match.group(1) in ['valid-deref', 'valid-free', 'valid-memtrack']:
                        newStatus = result.STR_FALSE + '(' + match.group(1) + ')'

                else:
                    newStatus = result.RESULT_UNKNOWN if not status.startswith('ERROR') else None
                if newStatus and not status:
                    status = newStatus

        if status == 'KILLED (UNKNOWN)':
            status = 'KILLED'
        if not status or undef:
            status = result.RESULT_UNKNOWN
        return status


if __name__ == "__main__":
    tool = Tool()
    executable = tool.executable()
    print('Executable: {0}'.format(os.path.abspath(executable)))
    print('Version: {0}'.format(tool.version(executable)))
