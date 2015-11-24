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
import os
import subprocess
import sys
import unittest
sys.dont_write_bytecode = True # prevent creation of .pyc files

from benchexec import check_cgroups

try:
    from subprocess import DEVNULL
except ImportError:
    DEVNULL = open(os.devnull, 'wb')

python = 'python2' if sys.version_info[0] == 2 else 'python3'

class TestCheckCgroups(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.longMessage = True
        cls.maxDiff = None
        logging.disable(logging.CRITICAL)

    def execute_run_extern(self, *args, **kwargs):
        try:
            return subprocess.check_output(
                    args=[python, '-m', 'benchexec.check_cgroups'] + list(args),
                    stderr=subprocess.STDOUT,
                    **kwargs
                    ).decode()
        except subprocess.CalledProcessError as e:
            if e.returncode != 1: # 1 is expected if cgroups are not available
                print(e.output.decode())
                raise e

    def test_extern_command(self):
        self.execute_run_extern()

    def test_simple(self):
        try:
            check_cgroups.main(['--no-thread'])
        except SystemExit as e:
            # expected if cgroups are not available
            self.skipTest(e)

    def test_threaded(self):
        try:
            check_cgroups.main([])
        except SystemExit as e:
            # expected if cgroups are not available
            self.skipTest(e)

    def test_thread_result_is_returned(self):
        """
        Test that an error raised by check_cgroup_availability is correctly
        re-raised in the main thread by replacing this function temporarily.
        """
        tmp = check_cgroups.check_cgroup_availability
        try:
            check_cgroups.check_cgroup_availability = lambda wait : exit(1)

            with self.assertRaises(SystemExit):
                check_cgroups.main([])

        finally:
            check_cgroups.check_cgroup_availability = tmp
