# BenchExec is a framework for reliable benchmarking.
# This file is part of BenchExec.
#
# Copyright (C) 2007-2016  Dirk Beyer
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

sys.dont_write_bytecode = True  # prevent creation of .pyc files

from benchexec.tablegenerator import util


class TestUnit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.longMessage = True
        cls.maxDiff = None

    def assertEqualNumberAndUnit(self, value, number, unit):
        self.assertEqual(util.split_number_and_unit(value), (number, unit))
        self.assertEqual(util.split_string_at_suffix(value, False), (number, unit))

    def assertEqualTextAndNumber(self, value, text, number):
        self.assertEqual(util.split_string_at_suffix(value, True), (text, number))

    def test_split_number_and_unit(self):
        self.assertEqualNumberAndUnit("", "", "")
        self.assertEqualNumberAndUnit("1", "1", "")
        self.assertEqualNumberAndUnit("1s", "1", "s")
        self.assertEqualNumberAndUnit("111s", "111", "s")
        self.assertEqualNumberAndUnit("s1", "s1", "")
        self.assertEqualNumberAndUnit("s111", "s111", "")
        self.assertEqualNumberAndUnit("-1s", "-1", "s")
        self.assertEqualNumberAndUnit("1abc", "1", "abc")
        self.assertEqualNumberAndUnit("abc", "", "abc")
        self.assertEqualNumberAndUnit("abc1abc", "abc1", "abc")
        self.assertEqualNumberAndUnit("abc1abc1abc", "abc1abc1", "abc")

    def test_split_string_at_suffix(self):
        self.assertEqualTextAndNumber("", "", "")
        self.assertEqualTextAndNumber("1", "", "1")
        self.assertEqualTextAndNumber("1s", "1s", "")
        self.assertEqualTextAndNumber("111s", "111s", "")
        self.assertEqualTextAndNumber("s1", "s", "1")
        self.assertEqualTextAndNumber("s111", "s", "111")
        self.assertEqualTextAndNumber("-1s", "-1s", "")
        self.assertEqualTextAndNumber("abc1", "abc", "1")
        self.assertEqualTextAndNumber("abc", "abc", "")
        self.assertEqualTextAndNumber("abc1abc", "abc1abc", "")
        self.assertEqualTextAndNumber("abc1abc1", "abc1abc", "1")
