"""
BenchExec is a framework for reliable benchmarking.
This file is part of BenchExec.

Copyright (C) 2007-2017  Dirk Beyer
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

import logging

import benchexec.result as result
import benchexec.util as util
import benchexec.tools.cpachecker as cpachecker
from benchexec.model import SOFTTIMELIMIT


class Tool(cpachecker.Tool):
    """
    Tool info for CPA-witness-exec.
    """

    def executable(self):
        super(Tool, self).executable()  # Makes sure that CPAchecker can be called, shows a warning otherwise
        return util.find_executable('cpa_witness_exec.py', 'scripts/cpa_witness_exec.py')

    def version(self, executable):
        stdout = self._version_from_tool(executable, '-version')
        return stdout

    def name(self):
        return 'CPA-Witness-Exec'

    def cmdline(self, executable, options, tasks, propertyfile=None, rlimits={}):
        additional_options = super(Tool, self)._get_additional_options(options, propertyfile, rlimits)
        # Add additional options in front of existing ones, since -gcc-args ... must be last argument in front of task
        return [executable] + additional_options + options + tasks

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        """
        @param returncode: code returned by CPA-witness-exec
        @param returnsignal: signal, which terminated CPA-witness-exec
        @param output: the output of CPA-witness-exec
        @return: status of CPA-witness-exec after executing a run
        """

        status = None
        for line in reversed(output):
            if line.startswith('Verification result: '):
                line = line[21:].strip()
                if line.startswith('FALSE'):
                    status = result.RESULT_FALSE_REACH
                else:
                    status = result.RESULT_UNKNOWN
                break

        if not status:
            status = result.RESULT_ERROR
        return status

