# BenchExec is a framework for reliable benchmarking.
# This file is part of BenchExec.
#
# Copyright (C) 2007-2015  Dirk Beyer
# All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# prepare for Python 3
from __future__ import absolute_import, division, print_function, unicode_literals

import logging
import sys
import unittest
sys.dont_write_bytecode = True # prevent creation of .pyc files

from benchexec.model import Run
from benchexec.result import *  # @UnusedWildImport
from benchexec.tools.template import BaseTool


class TestResult(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.longMessage = True
        logging.disable(logging.CRITICAL)

    def create_run(self, info_result=RESULT_UNKNOWN):
        # lambdas are simple dummy objects
        runSet = lambda: None
        runSet.log_folder = '.'
        runSet.options = []
        runSet.real_name = None
        runSet.propertyfile = None
        runSet.benchmark = lambda: None
        runSet.benchmark.base_dir = '.'
        runSet.benchmark.benchmark_file = 'Test.xml'
        runSet.benchmark.columns = []
        runSet.benchmark.name = 'Test'
        runSet.benchmark.instance = 'Test'
        runSet.benchmark.rlimits = {}
        runSet.benchmark.tool = BaseTool()
        def determine_result(self, returncode, returnsignal, output, isTimeout=False):
            return info_result
        runSet.benchmark.tool.determine_result = determine_result

        return Run(sourcefiles=['test.c'], fileOptions=[], runSet=runSet)

    def test_simple(self):
        run = self.create_run(info_result=RESULT_UNKNOWN)
        self.assertEqual(RESULT_UNKNOWN, run._analyse_result(0, '', False, None))

        run = self.create_run(info_result=RESULT_TRUE_PROP)
        self.assertEqual(RESULT_TRUE_PROP, run._analyse_result(0, '', False, None))

        run = self.create_run(info_result=RESULT_FALSE_REACH)
        self.assertEqual(RESULT_FALSE_REACH, run._analyse_result(0, '', False, None))

    def test_timeout(self):
        run = self.create_run(info_result=RESULT_UNKNOWN)
        self.assertEqual('TIMEOUT', run._analyse_result(0, '', True, None))

        run = self.create_run(info_result=RESULT_TRUE_PROP)
        self.assertEqual('TIMEOUT (true)', run._analyse_result(0, '', True, None))

        run = self.create_run(info_result=RESULT_FALSE_REACH)
        self.assertEqual('TIMEOUT (false(reach))', run._analyse_result(0, '', True, None))

        run = self.create_run(info_result='SOME OTHER RESULT')
        self.assertEqual('SOME OTHER RESULT', run._analyse_result(0, '', True, None))

    def test_out_of_memory(self):
        run = self.create_run(info_result=RESULT_UNKNOWN)
        self.assertEqual('OUT OF MEMORY', run._analyse_result(0, '', False, 'memory'))

        run = self.create_run(info_result=RESULT_TRUE_PROP)
        self.assertEqual('OUT OF MEMORY (true)', run._analyse_result(0, '', False, 'memory'))

        run = self.create_run(info_result=RESULT_FALSE_REACH)
        self.assertEqual('OUT OF MEMORY (false(reach))', run._analyse_result(0, '', False, 'memory'))

        run = self.create_run(info_result='SOME OTHER RESULT')
        self.assertEqual('SOME OTHER RESULT', run._analyse_result(0, '', False, 'memory'))

    def test_timeout_and_out_of_memory(self):
        run = self.create_run(info_result=RESULT_UNKNOWN)
        self.assertEqual('TIMEOUT', run._analyse_result(0, '', True, 'memory'))

        run = self.create_run(info_result=RESULT_TRUE_PROP)
        self.assertEqual('TIMEOUT (true)', run._analyse_result(0, '', True, 'memory'))

        run = self.create_run(info_result=RESULT_FALSE_REACH)
        self.assertEqual('TIMEOUT (false(reach))', run._analyse_result(0, '', True, 'memory'))

        run = self.create_run(info_result='SOME OTHER RESULT')
        self.assertEqual('SOME OTHER RESULT', run._analyse_result(0, '', False, 'memory'))

    def test_returnsignal(self):
        def signal(sig):
            """Encode a signal as it would be returned by os.wait"""
            return sig

        run = self.create_run(info_result=RESULT_UNKNOWN)
        self.assertEqual('TIMEOUT', run._analyse_result(signal(9), '', True, None))

        run = self.create_run(info_result=RESULT_UNKNOWN)
        self.assertEqual('OUT OF MEMORY', run._analyse_result(signal(9), '', False, 'memory'))

        run = self.create_run(info_result=RESULT_TRUE_PROP)
        self.assertEqual(RESULT_TRUE_PROP, run._analyse_result(signal(9), '', False, None))

        run = self.create_run(info_result=RESULT_FALSE_REACH)
        self.assertEqual(RESULT_FALSE_REACH, run._analyse_result(signal(9), '', False, None))

        run = self.create_run(info_result='SOME OTHER RESULT')
        self.assertEqual('SOME OTHER RESULT', run._analyse_result(signal(9), '', False, None))

        run = self.create_run(info_result=RESULT_UNKNOWN)
        self.assertEqual('KILLED BY SIGNAL 9', run._analyse_result(signal(9), '', False, None))

    def test_exitcode(self):
        def exitcode(code):
            """Encode an exit of aprogram as it would be returned by os.wait"""
            return code << 8

        run = self.create_run(info_result=RESULT_UNKNOWN)
        self.assertEqual('TIMEOUT', run._analyse_result(exitcode(1), '', True, None))

        run = self.create_run(info_result=RESULT_UNKNOWN)
        self.assertEqual('OUT OF MEMORY', run._analyse_result(exitcode(1), '', False, 'memory'))

        run = self.create_run(info_result=RESULT_TRUE_PROP)
        self.assertEqual(RESULT_TRUE_PROP, run._analyse_result(exitcode(1), '', False, None))

        run = self.create_run(info_result=RESULT_FALSE_REACH)
        self.assertEqual(RESULT_FALSE_REACH, run._analyse_result(exitcode(1), '', False, None))

        run = self.create_run(info_result='SOME OTHER RESULT')
        self.assertEqual('SOME OTHER RESULT', run._analyse_result(exitcode(1), '', False, None))

        run = self.create_run(info_result=RESULT_UNKNOWN)
        self.assertEqual('ERROR (1)', run._analyse_result(exitcode(1), '', False, None))
