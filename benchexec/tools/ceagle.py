#!/usr/bin/env python
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

import benchexec.result as result
import benchexec.util as util
import benchexec.tools.template

class Tool(benchexec.tools.template.BaseTool):
    """
    Tool wrapper for Ceagle.
    It has additional features such as building CPAchecker before running it
    if executed within a source checkout.
    It also supports extracting data from the statistics output of CPAchecker
    for adding it to the result tables.
    """

    def executable(self):
        return util.find_executable('ceagle.sh')


    def version(self, executable):
        return '1.0'

    def name(self):
        return 'Ceagle'


    def cmdline(self, executable, options, tasks, propertyfile, rlimits):
        return [executable] + tasks


    def determine_result(self, returncode, returnsignal, output, isTimeout):
        """
        @param returncode: code returned by Ceagle
        @param returnsignal: signal, which terminated Ceagle
        @param output: the output of Ceagle
        @return: status of Ceagle after executing a run
        """
        status = result.RESULT_UNKNOWN
        stroutput = str(output)

        if isTimeout:
            status = 'TIMEOUT'
        elif 'TRUE' in stroutput:
            status = result.RESULT_TRUE_PROP
        elif 'FALSE' in stroutput:
            status = result.RESULT_FALSE_REACH
        elif 'UNKNOWN' in stroutput:
            status = result.RESULT_UNKNOWN
        else:
            assert(False)

        return status
