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

import sys
import unittest
sys.dont_write_bytecode = True # prevent creation of .pyc files

from benchexec import util

class TestParse(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.longMessage = True
        cls.maxDiff = None

    def assertEqualNumberAndUnit(self, value, number, unit):
        self.assertEqual(util.split_number_and_unit(value), (number, unit))

    def test_split_number_and_unit(self):
        self.assertEqualNumberAndUnit("1", 1, "")
        self.assertEqualNumberAndUnit("1s", 1, "s")
        self.assertEqualNumberAndUnit("  1  s  ", 1, "s")
        self.assertEqualNumberAndUnit("-1s", -1, "s")
        self.assertEqualNumberAndUnit("1abc", 1, "abc")
        self.assertEqualNumberAndUnit("1  abc  ", 1, "abc")

        self.assertRaises(ValueError, util.split_number_and_unit, "")
        self.assertRaises(ValueError, util.split_number_and_unit, "abc")
        self.assertRaises(ValueError, util.split_number_and_unit, "s")
        self.assertRaises(ValueError, util.split_number_and_unit, "- 1")
        self.assertRaises(ValueError, util.split_number_and_unit, "a1a")


    def test_parse_memory_value(self):
        self.assertEqual(util.parse_memory_value("1"), 1)
        self.assertEqual(util.parse_memory_value("1B"), 1)
        self.assertEqual(util.parse_memory_value("1kB"), 1000)
        self.assertEqual(util.parse_memory_value("1MB"), 1000*1000)
        self.assertEqual(util.parse_memory_value("1GB"), 1000*1000*1000)
        self.assertEqual(util.parse_memory_value("1TB"), 1000*1000*1000*1000)


    def test_parse_timespan_value(self):
        self.assertEqual(util.parse_timespan_value("1"), 1)
        self.assertEqual(util.parse_timespan_value("1s"), 1)
        self.assertEqual(util.parse_timespan_value("1min"), 60)
        self.assertEqual(util.parse_timespan_value("1h"), 60*60)
        self.assertEqual(util.parse_timespan_value("1d"), 24*60*60)
