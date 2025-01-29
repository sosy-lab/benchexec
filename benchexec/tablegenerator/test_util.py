# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

from decimal import Decimal
import unittest

from benchexec.tablegenerator import util


class TestUnit(unittest.TestCase):

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

    def test_roman_number_conversion(self):
        test_data = {
            1: "I",
            2: "II",
            3: "III",
            4: "IV",
            5: "V",
            6: "VI",
            7: "VII",
            8: "VIII",
            9: "IX",
            10: "X",
            11: "XI",
            14: "XIV",
            21: "XXI",
            49: "XLIX",
            50: "L",
            99: "XCIX",
            100: "C",
            849: "DCCCXLIX",
            999: "CMXCIX",
            1000: "M",
            3000: "MMM",
            3333: "MMMCCCXXXIII",
            10_001: "MMMMMMMMMMI",
        }

        for k, v in test_data.items():
            self.assertEqual(v, util.number_to_roman_string(k))
            self.assertEqual(str(v), util.number_to_roman_string(k))

        self.assertRaises(ValueError, util.number_to_roman_string, -1)
        self.assertRaises(ValueError, util.number_to_roman_string, 0)

        self.assertRaises(ValueError, util.number_to_roman_string, "forty-two")

    def test_cap_first_letter(self):
        test_data = {
            "test": "Test",
            "tHis is gREAT": "THis is gREAT",
            "BIG WORD": "BIG WORD",
            " leading space": " leading space",
            "": "",
        }
        for k, v in test_data.items():
            self.assertEqual(v, util.cap_first_letter(k))

    def test_merge_lists(self):
        l = (1, 2, 3)  # make sure merge_lists does not modify it # noqa: E741
        self.assertListEqual(list(l), util.merge_lists([l]))
        self.assertListEqual(list(l), util.merge_lists([l, l]))
        self.assertListEqual(list(l), util.merge_lists([l, l, l, l, l, l, l]))
        self.assertListEqual(list(l), util.merge_lists([[], l, l, []]))
        self.assertListEqual(list(l), util.merge_lists([[1, 2, 3], [1, 2], [1]]))
        self.assertListEqual(list(l), util.merge_lists([[1, 2, 3], [2, 3], [3]]))
        self.assertListEqual(list(l), util.merge_lists([[1], [1, 2], [1, 2, 3]]))
        self.assertListEqual(list(l), util.merge_lists([[3], [2, 3], [1, 2, 3]]))
        self.assertListEqual(
            [1, 2, 3, 4, 5, 6], util.merge_lists([[1, 2, 4, 6], [1, 2, 3, 4, 5]])
        )

    def test_find_common_elements(self):
        self.assertListEqual([], util.find_common_elements([[]]))
        self.assertListEqual([], util.find_common_elements([[], [1, 2, 3]]))
        self.assertListEqual([], util.find_common_elements([[], [1, 2, 3], [1, 2, 3]]))
        self.assertListEqual([], util.find_common_elements([[1, 2, 3], [1, 2, 3], []]))
        self.assertListEqual([], util.find_common_elements([[1], [2], [3]]))
        self.assertListEqual([1, 2, 3], util.find_common_elements([[1, 2, 3]]))
        self.assertListEqual(
            [1, 2, 3], util.find_common_elements([[1, 2, 3], [1, 2, 3]])
        )
        self.assertListEqual(
            [1, 2, 3], util.find_common_elements([[1, 2, 3, 4], [1, 2, 3, 5]])
        )

    def test_to_decimal_empty(self):
        self.assertIsNone(util.to_decimal(None))
        self.assertIsNone(util.to_decimal(""))
        self.assertIsNone(util.to_decimal(" "))

    def test_to_decimal_str(self):
        self.assertTrue(util.to_decimal("NaN").is_nan())
        self.assertTrue(util.to_decimal(" NaN ").is_nan())
        self.assertEqual(Decimal("+Inf"), util.to_decimal("Inf"))
        self.assertEqual(Decimal("+Inf"), util.to_decimal(" Inf "))
        self.assertEqual(Decimal("+Inf"), util.to_decimal("+inf"))
        self.assertEqual(Decimal("-Inf"), util.to_decimal("-inf"))
        self.assertEqual(Decimal("1.234"), util.to_decimal("1.234"))
        self.assertEqual(Decimal("1.234"), util.to_decimal(" 1.234 s "))
        self.assertEqual(Decimal("1.234"), util.to_decimal("+1.234"))
        self.assertEqual(Decimal("-1.234"), util.to_decimal("-1.234"))

    def test_to_decimal_numeric(self):
        self.assertEqual(Decimal("-1"), util.to_decimal(-1))
        self.assertEqual(Decimal(-1.234), util.to_decimal(-1.234))
        self.assertEqual(Decimal("-1.234"), util.to_decimal(Decimal("-1.234")))
