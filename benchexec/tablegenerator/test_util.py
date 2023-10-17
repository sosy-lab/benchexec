# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

from decimal import Decimal
from benchexec.tablegenerator import util
import pytest


class TestUnit:
    def test_split_number_and_unit(self):
        assert util.split_number_and_unit("") == ("", "")
        assert util.split_number_and_unit("1") == ("1", "")
        assert util.split_number_and_unit("1s") == ("1", "s")
        assert util.split_number_and_unit("111s") == ("111", "s")
        assert util.split_number_and_unit("s1") == ("s1", "")
        assert util.split_number_and_unit("s111") == ("s111", "")
        assert util.split_number_and_unit("-1s") == ("-1", "s")
        assert util.split_number_and_unit("1abc") == ("1", "abc")
        assert util.split_number_and_unit("abc") == ("", "abc")
        assert util.split_number_and_unit("abc1abc") == ("abc1", "abc")
        assert util.split_number_and_unit("abc1abc1abc") == ("abc1abc1", "abc")

    def test_split_string_at_suffix(self):
        assert util.split_string_at_suffix("") == ("", "")
        assert util.split_string_at_suffix("1") == ("", "1")
        assert util.split_string_at_suffix("1s") == ("1s", "")
        assert util.split_string_at_suffix("111s") == ("111s", "")
        assert util.split_string_at_suffix("s1") == ("s", "1")
        assert util.split_string_at_suffix("s111") == ("s", "111")
        assert util.split_string_at_suffix("-1s") == ("-1s", "")
        assert util.split_string_at_suffix("abc1") == ("abc", "1")
        assert util.split_string_at_suffix("abc") == ("abc", "")
        assert util.split_string_at_suffix("abc1abc") == ("abc1abc", "")
        assert util.split_string_at_suffix("abc1abc1") == ("abc1abc", "1")

    def test_print_decimal_roundtrip(self):
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
            assert expected == util.print_decimal(Decimal(value))

    def test_print_decimal_int(self):
        test_values = ["0e0", "-0e0", "0e20", "1e0", "1e20", "0e10"]
        for value in test_values:
            value = Decimal(value)
            expected = str(value.quantize(1))
            assert "e" not in expected
            assert expected == util.print_decimal(value)

    def test_print_decimal_float(self):
        test_values = ["1e-4", "123e-4", "1234e-4", "1234e-5", "1234e-6"]
        for value in test_values:
            expected = str(float(value))
            assert "e" not in expected
            assert expected == util.print_decimal(Decimal(value))

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
            assert v == util.number_to_roman_string(k)
            assert str(v) == util.number_to_roman_string(k)

        with pytest.raises(ValueError):
            util.number_to_roman_string(-1)
        with pytest.raises(ValueError):
            util.number_to_roman_string(0)

        with pytest.raises(ValueError):
            util.number_to_roman_string("forty-two")

    def test_cap_first_letter(self):
        test_data = {
            "test": "Test",
            "tHis is gREAT": "THis is gREAT",
            "BIG WORD": "BIG WORD",
            " leading space": " leading space",
            "": "",
        }
        for k, v in test_data.items():
            assert v == util.cap_first_letter(k)

    def test_merge_lists(self):
        l1 = (1, 2, 3)
        assert list(l1) == util.merge_lists([l1])
        assert list(l1) == util.merge_lists([l1, l1])
        assert list(l1) == util.merge_lists([l1, l1, l1, l1, l1, l1, l1])
        assert list(l1) == util.merge_lists([[], l1, l1, []])
        assert list(l1) == util.merge_lists([[1, 2, 3], [1, 2], [1]])
        assert list(l1) == util.merge_lists([[1, 2, 3], [2, 3], [3]])
        assert list(l1) == util.merge_lists([[1], [1, 2], [1, 2, 3]])
        assert list(l1) == util.merge_lists([[3], [2, 3], [1, 2, 3]])
        assert [1, 2, 3, 4, 5, 6] == util.merge_lists([[1, 2, 4, 6], [1, 2, 3, 4, 5]])

    def test_find_common_elements(self):
        assert [] == util.find_common_elements([[]])
        assert [] == util.find_common_elements([[], [1, 2, 3]])
        assert [] == util.find_common_elements([[], [1, 2, 3], [1, 2, 3]])
        assert [] == util.find_common_elements([[1, 2, 3], [1, 2, 3], []])
        assert [] == util.find_common_elements([[1], [2], [3]])
        assert [1, 2, 3] == util.find_common_elements([[1, 2, 3]])
        assert [1, 2, 3] == util.find_common_elements([[1, 2, 3], [1, 2, 3]])
        assert [1, 2, 3] == util.find_common_elements([[1, 2, 3, 4], [1, 2, 3, 5]])
