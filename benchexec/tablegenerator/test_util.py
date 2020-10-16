# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import sys
import unittest

from benchexec.tablegenerator import util

sys.dont_write_bytecode = True  # prevent creation of .pyc files


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
