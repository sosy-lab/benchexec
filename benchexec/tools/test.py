# BenchExec is a framework for reliable benchmarking.
# This file is part of BenchExec.
#
# Copyright (C) 2007-2018  Dirk Beyer
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
import unittest
import sys

import benchexec.model

sys.dont_write_bytecode = True # prevent creation of .pyc files

here = os.path.dirname(__file__)


class ToolInfoModuleTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.longMessage = True
        cls.maxDiff = None

    def test_load_tool_info_module(self):
        """Test whether all tool-info modules can be loaded"""
        files = os.listdir(here)
        for file_name in files:
            tool_info_name = os.path.splitext(file_name)
            if tool_info_name[1] != ".py" or file_name == os.path.basename(__file__):
                continue

            try:
                benchexec.model.load_tool_info(tool_info_name[0])
            except SystemExit as e:
                logging.warning("Cannot load tool-info module %s: %s", tool_info_name, e)
            except BaseException as e:
                self.fail("Loading tool-info module {} failed: {}".format(tool_info_name, e))
