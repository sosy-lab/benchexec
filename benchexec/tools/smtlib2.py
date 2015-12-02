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

import benchexec.result as result
import benchexec.tools.template

class Smtlib2Tool(benchexec.tools.template.BaseTool):
    """
    Abstract base class for tool infos for SMTLib2-compatible solvers.
    These tools share a common output format, which is implemented here.
    """

    def determine_result(self, returncode, returnsignal, output, isTimeout):

        if returnsignal == 0 and returncode == 0:
            status = None
            for line in output:
                line = line.strip()
                if line == 'unsat':
                    status = result.RESULT_UNSAT
                elif line == 'sat':
                    status = result.RESULT_SAT
                elif not status and line.startswith('(error '):
                    status = 'ERROR'

            if not status:
                status = result.RESULT_UNKNOWN

        elif ((returnsignal == 9) or (returnsignal == 15)) and isTimeout:
            status = 'TIMEOUT'

        elif returnsignal == 9:
            status = "KILLED BY SIGNAL 9"
        elif returnsignal == 6:
            status = "ABORTED"
        elif returnsignal == 15:
            status = "KILLED"
        else:
            status = "ERROR ({0})".format(returncode)

        return status