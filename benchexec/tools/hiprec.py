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
    Tool info for HIPrec.
    """

    REQUIRED_PATHS = [
                  "fixcalc",
                  "hiprec",
                  "hiprec_run.sh",
                  "oc",
                  "prelude.ss",
                  "z3-4.3.2"
                  ]

    def executable(self):
        executable = util.find_executable('hiprec')
        return executable


    def name(self):
        return 'HIPrec'


    def cmdline(self, executable, options, tasks, propertyfile=None, rlimits={}):
       return [executable] + options + tasks + ['--debug']


    def determine_result(self, returncode, returnsignal, output, isTimeout):
        status = result.RESULT_UNKNOWN
        for line in output:
            if line.startswith('Verification result:('):
                line = line[21:].strip()
                if line.startswith('TRUE'):
                    status = result.RESULT_TRUE_PROP
                elif line.startswith('FALSE'):
                    status = result.RESULT_FALSE_REACH
                else:
                    status = result.RESULT_UNKNOWN

        return status
