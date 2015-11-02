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

# prepare for Python 3
from __future__ import absolute_import, division, print_function, unicode_literals

import logging
import subprocess
import sys
import os
import re

import benchexec.util as util
import benchexec.tools.template
import benchexec.result as result


sys.dont_write_bytecode = True # prevent creation of .pyc files

if __name__ == "__main__":
    sys.path.append(os.path.join(os.path.dirname(__file__), os.path.pardir, os.path.pardir))

import benchexec.result as result
import benchexec.util as util
import benchexec.tools.template
from benchexec.model import SOFTTIMELIMIT

REQUIRED_PATHS = [
                  "hiprec",
                 ]

class Tool(benchexec.tools.template.BaseTool):
    """
    Tool wrapper for HIPrec.
    """

    def executable(self):
        executable = util.find_executable('hiprec')
        return executable


    def working_directory(self, executable):
        return os.curdir


    def name(self):
        return 'hiprec'


    def cmdline(self, executable, options, tasks, propertyfile=None, rlimits={}):
       return [executable] + options + tasks


    def determine_result(self, returncode, returnsignal, output, isTimeout):
        """
        @param returncode: code returned by CPAchecker
        @param returnsignal: signal, which terminated CPAchecker
        @param output: the output of CPAchecker
        @return: status of CPAchecker after executing a run
        """

        for line in output:
            if line.startswith('Verification result: '):
                line = line[22:].strip()
                if line.startswith('TRUE'):
                    newStatus = result.RESULT_TRUE_PROP
                elif line.startswith('FALSE'):
                    newStatus = result.RESULT_FALSE_REACH
                else:
                    newStatus = result.RESULT_UNKNOWN

                if not status:
                    status = newStatus
                elif newStatus != result.RESULT_UNKNOWN:
                    status = "{0} ({1})".format(status, newStatus)

        if not status:
            status = result.RESULT_UNKNOWN
        return status
