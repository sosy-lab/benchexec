# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

from decimal import Decimal
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

    def test_print_decimal_roundtrip(self):
        # These values should be printed exactly as in the input (with "+" removed)
        test_values = [
            "NaN",
            "Inf",
            "-Inf",
            "+Inf",
            "0",
            "-0",
            "+0",
            "0.0",
            "-0.0",
            "0.00000000000000000000",
            "0.00000000000000000001",
            "0.00000000123450000000",
            "0.1",
            "0.10000000000000000000",
            "0.99999999999999999999",
            "1",
            "-1",
            "+1",
            "1000000000000000000000",
            "10000000000.0000000000",
        ]
        for value in test_values:
            expected = value.lstrip("+")
            self.assertEqual(expected, util.print_decimal(Decimal(value)))

    def test_print_decimal_int(self):
        # These values should be printed like Decimal prints them after quantizing
        # to remove the exponent.
        test_values = ["0e0", "-0e0", "0e20", "1e0", "1e20", "0e10"]
        for value in test_values:
            value = Decimal(value)
            expected = str(value.quantize(1))
            assert "e" not in expected
            self.assertEqual(expected, util.print_decimal(value))

    def test_print_decimal_float(self):
        # These values should be printed like str prints floats.
        test_values = ["1e-4", "123e-4", "1234e-4", "1234e-5", "1234e-6"]
        for value in test_values:
            expected = str(float(value))
            assert "e" not in expected, expected
            self.assertEqual(expected, util.print_decimal(Decimal(value)))
