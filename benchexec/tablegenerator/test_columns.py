# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

from decimal import Decimal
import unittest

from benchexec.tablegenerator.columns import (
    Column,
    ColumnType,
    ColumnMeasureType,
)
from benchexec.tablegenerator.util import TableDefinitionError

nan = Decimal("nan")
inf = Decimal("inf")


class ColumnsTest(unittest.TestCase):
    def setUp(self):
        self.max_dec_digits = 6
        self.sig_figures = 4
        self.measure_type = ColumnMeasureType(self.max_dec_digits)
        self.measure_column = Column(
            "CpuTime", None, self.sig_figures, None, self.measure_type, None, None, 1
        )
        self.default_optionals = ("html",)

    def tearDown(self):
        pass

    def test_format_value_none(self):
        formatted_value_none = self.measure_column.format_value(
            None, *self.default_optionals
        )
        self.assertEqual(formatted_value_none, "")

    def test_format_value_no_align(self):
        formatted_value_no_align = self.measure_column.format_value(
            "1.555s", *self.default_optionals
        )
        self.assertEqual(formatted_value_no_align, "1.555")

    def test_format_value_no_align_rounded(self):
        formatted_value_no_align_rounded = self.measure_column.format_value(
            "0.55559", *self.default_optionals
        )
        self.assertEqual(formatted_value_no_align_rounded, "0.5556")

    def test_format_value_round_up(self):
        formatted_value_no_align_zeros_cut = self.measure_column.format_value(
            "5.7715", *self.default_optionals
        )
        self.assertEqual(formatted_value_no_align_zeros_cut, "5.772")

    def test_format_value_round_up2(self):
        formatted_value_no_align_zeros_cut = self.measure_column.format_value(
            "4.4445", *self.default_optionals
        )
        self.assertEqual(formatted_value_no_align_zeros_cut, "4.445")

    def test_format_value_round_up3(self):
        formatted_value_no_align_zeros_cut = self.measure_column.format_value(
            "99.675", *self.default_optionals
        )
        self.assertEqual(formatted_value_no_align_zeros_cut, "99.68")

    def test_format_value_add_missing_zeros(self):
        formatted_value_no_align_zeros_cut = self.measure_column.format_value(
            "9.599999", *self.default_optionals
        )
        self.assertEqual(formatted_value_no_align_zeros_cut, "9.600")

    def test_format_value_trailing_zeros(self):
        formatted_value = self.measure_column.format_value(
            "1.600", *self.default_optionals
        )
        self.assertEqual(formatted_value, "1.600")

    def test_format_value_more_trailing_zeros(self):
        formatted_value = self.measure_column.format_value(
            "1.60000", *self.default_optionals
        )
        self.assertEqual(formatted_value, "1.600")

    def test_format_value_less_trailing_zeros(self):
        formatted_value = self.measure_column.format_value(
            "1.6", *self.default_optionals
        )
        self.assertEqual(formatted_value, "1.6")

    def test_format_value_more_trailing_zeros2(self):
        formatted_value = self.measure_column.format_value(
            "160.00", *self.default_optionals
        )
        self.assertEqual(formatted_value, "160.0")

    def test_format_value_less_trailing_zeros2(self):
        formatted_value = self.measure_column.format_value(
            "160", *self.default_optionals
        )
        self.assertEqual(formatted_value, "160")

    def test_format_value_zero(self):
        formatted_value = self.measure_column.format_value("0", *self.default_optionals)
        self.assertEqual(formatted_value, "0")

    def test_format_value_precise_zero(self):
        formatted_value = self.measure_column.format_value(
            "0.0000", *self.default_optionals
        )
        self.assertEqual(formatted_value, "0.0000")

    def test_format_value_more_precise_zero(self):
        formatted_value = self.measure_column.format_value(
            "0.0000000", *self.default_optionals
        )
        self.assertEqual(formatted_value, "0.0000")

    def test_format_value_small_number(self):
        formatted_value = self.measure_column.format_value(
            "0.00000000001", *self.default_optionals
        )
        self.assertEqual(formatted_value, "0.00000000001")

    def test_format_value_many_digits(self):
        formatted_value_no_align_rounded = self.measure_column.format_value(
            "0.09999999999999999", *self.default_optionals
        )
        self.assertEqual(formatted_value_no_align_rounded, "0.1000")

    def test_format_value_align_decimal(self):
        formatted_value_aligned = self.measure_column.format_value(
            "1.555s", "html_cell"
        )
        self.assertEqual(formatted_value_aligned, "1.555&#x2007;&#x2007;&#x2007;")

    def test_format_value_small_value(self):
        small_value = "0.000008767"
        small_value_measure_type = ColumnMeasureType(len(small_value) - 3)
        small_value_column = Column(
            "CpuTime",
            None,
            3,
            None,
            small_value_measure_type,
            unit=None,
            scale_factor=1,
        )
        formatted_value = small_value_column.format_value(
            small_value, *self.default_optionals
        )
        self.assertEqual(formatted_value, "0.00000877")

        # Test CSV formatting with scaling
        small_value_column = Column(
            "CpuTime",
            None,
            None,
            None,
            small_value_measure_type,
            unit="s",
            scale_factor=Decimal("0.1"),
        )
        formatted_value = small_value_column.format_value(small_value, "csv")
        self.assertEqual(formatted_value, "0.0000008767")

        # Test whether scaling to small values and resulting values are handled correctly
        small_value_measure_type = ColumnMeasureType(12)
        small_value_column = Column(
            "CpuTime",
            None,
            3,
            None,
            small_value_measure_type,
            unit="dummy",
            scale_factor=1e-10,
        )
        formatted_value_aligned = small_value_column.format_value("2", "html_cell")
        self.assertEqual(formatted_value_aligned, ".0000000002&#x2007;&#x2007;")

    def test_invalid_rounding_mode(self):
        import decimal

        decimal.getcontext().rounding = decimal.ROUND_HALF_DOWN
        formatted_value_no_align_zeros_cut = self.measure_column.format_value(
            "5.7715", *self.default_optionals
        )
        self.assertEqual(formatted_value_no_align_zeros_cut, "5.772")

    def test_format_value_align_int(self):
        formatted_value_int_aligned = self.measure_column.format_value(
            "20", "html_cell"
        )
        self.assertEqual(
            formatted_value_int_aligned,
            "20&#x2008;&#x2007;&#x2007;&#x2007;&#x2007;&#x2007;&#x2007;",
        )

    def test_format_value_cut_0_at_front(self):
        formatted_value_0_cut = self.measure_column.format_value(
            "0.055999", "html_cell"
        )
        self.assertEqual(formatted_value_0_cut, ".05600&#x2007;")

    def test_format_value_two_significant_figures(self):
        self.measure_column_two_sig_figures = Column(
            "CpuTime", None, 2, None, self.measure_type, None, None, 1
        )
        formatted_value_decimals_cut = self.measure_column_two_sig_figures.format_value(
            "9.99999", *self.default_optionals
        )
        self.assertEqual(formatted_value_decimals_cut, "10")

    def test_format_value_no_sigs(self):
        self.measure_column_no_sigs = Column(
            "CpuTime", None, None, None, self.measure_type, None, None, 1
        )
        formatted_value_rounding = self.measure_column_no_sigs.format_value(
            "9999.12015s", *self.default_optionals
        )
        self.assertEqual(formatted_value_rounding, "10000")

    def test_format_value_negative_float(self):
        formatted_value = self.measure_column.format_value(
            "-0.05559", *self.default_optionals
        )
        self.assertEqual(formatted_value, "-0.05559")

        formatted_value = self.measure_column.format_value(
            "-0.055593", *self.default_optionals
        )
        self.assertEqual(formatted_value, "-0.05559")

        formatted_value = self.measure_column.format_value(
            "-0.055598", *self.default_optionals
        )
        self.assertEqual(formatted_value, "-0.05560")

        formatted_value = self.measure_column.format_value(
            "-0.0555", *self.default_optionals
        )
        self.assertEqual(formatted_value, "-0.0555")

    def test_format_value_NaN(self):
        formatted_value = self.measure_column.format_value(
            "Nan", *self.default_optionals
        )
        self.assertEqual(formatted_value, "NaN")

    def test_format_value_inf(self):
        formatted_value = self.measure_column.format_value(
            "InF", *self.default_optionals
        )
        self.assertEqual(formatted_value, "Inf")

        formatted_value = self.measure_column.format_value(
            "inf", *self.default_optionals
        )
        self.assertEqual(formatted_value, "Inf")

        formatted_value = self.measure_column.format_value(
            "inF", *self.default_optionals
        )
        self.assertEqual(formatted_value, "Inf")

        formatted_value = self.measure_column.format_value(
            "+Inf", *self.default_optionals
        )
        self.assertEqual(formatted_value, "Inf")

    def test_format_value_negative_inf(self):
        formatted_value = self.measure_column.format_value(
            "-InF", *self.default_optionals
        )
        self.assertEqual(formatted_value, "-Inf")

        formatted_value = self.measure_column.format_value(
            "-inf", *self.default_optionals
        )
        self.assertEqual(formatted_value, "-Inf")

        formatted_value = self.measure_column.format_value(
            "-inF", *self.default_optionals
        )
        self.assertEqual(formatted_value, "-Inf")

        formatted_value = self.measure_column.format_value(
            "-Inf", *self.default_optionals
        )
        self.assertEqual(formatted_value, "-Inf")

        formatted_value = self.measure_column.format_value(
            "-inf", *self.default_optionals
        )
        self.assertEqual(formatted_value, "-Inf")

        formatted_value = self.measure_column.format_value(
            "-INF", *self.default_optionals
        )
        self.assertEqual(formatted_value, "-Inf")

    def test_format_value_NaN_for_csv(self):
        formatted_value = self.measure_column.format_value("Nan", "csv")
        self.assertEqual(formatted_value, "NaN")

    def test_format_value_inf_for_csv(self):
        formatted_value = self.measure_column.format_value("InF", "csv")
        self.assertEqual(formatted_value, "Inf")

        formatted_value = self.measure_column.format_value("inf", "csv")
        self.assertEqual(formatted_value, "Inf")

        formatted_value = self.measure_column.format_value("inF", "csv")
        self.assertEqual(formatted_value, "Inf")

        formatted_value = self.measure_column.format_value("+Inf", "csv")
        self.assertEqual(formatted_value, "Inf")

    def test_format_value_negative_inf_for_csv(self):
        formatted_value = self.measure_column.format_value("-InF", "csv")
        self.assertEqual(formatted_value, "-Inf")

        formatted_value = self.measure_column.format_value("-inf", "csv")
        self.assertEqual(formatted_value, "-Inf")

        formatted_value = self.measure_column.format_value("-inF", "csv")
        self.assertEqual(formatted_value, "-Inf")

        formatted_value = self.measure_column.format_value("-Inf", "csv")
        self.assertEqual(formatted_value, "-Inf")

        formatted_value = self.measure_column.format_value("-inf", "csv")
        self.assertEqual(formatted_value, "-Inf")

        formatted_value = self.measure_column.format_value("-INF", "csv")
        self.assertEqual(formatted_value, "-Inf")

    def test_format_value_tooltip_explicit_sigs(self):
        formatted_value_tooltip_considers_explicit_sigs = (
            self.measure_column.format_value("9999.125s", "tooltip_stochastic")
        )
        self.assertEqual(formatted_value_tooltip_considers_explicit_sigs, "9999")

    def test_format_value_tooltip_explicit_sigs2(self):
        formatted_value_tooltip_considers_explicit_sigs = (
            self.measure_column.format_value("0.125s", "tooltip_stochastic")
        )
        self.assertEqual(formatted_value_tooltip_considers_explicit_sigs, "0.125")

    def test_format_value_tooltip_explicit_sigs3(self):
        formatted_value_tooltip_considers_explicit_sigs = (
            self.measure_column.format_value("0.125999s", "tooltip_stochastic")
        )
        self.assertEqual(formatted_value_tooltip_considers_explicit_sigs, "0.1260")

    def test_format_value_count_alignment(self):
        count_column = Column(
            "memUsed", None, None, None, ColumnType.count, None, None, 1
        )
        formatted_value_count_no_align_no_sigs = count_column.format_value(
            "123456789", *self.default_optionals
        )
        self.assertEqual(formatted_value_count_no_align_no_sigs, "123456789")

        formatted_value_aligned = count_column.format_value("123456789", "html_cell")
        self.assertEqual(
            formatted_value_aligned, formatted_value_count_no_align_no_sigs
        )

    def test_format_value_count_sigs(self):
        count_column_sigs = Column(
            "memUsed", None, 3, None, ColumnType.count, None, None, 1
        )
        formatted_value_count_sigs = count_column_sigs.format_value(
            "123456789", *self.default_optionals
        )
        self.assertEqual(formatted_value_count_sigs, "123000000")

    def test_format_value_scale_values_down(self):
        scaling_column_smaller = Column(
            "memUsed", None, None, None, self.measure_type, "MB", None, "0.0000001"
        )
        formatted_value_scaled = scaling_column_smaller.format_value(
            "123456789", *self.default_optionals
        )
        self.assertEqual(formatted_value_scaled, "12.3")

    def test_format_value_scale_values_up(self):
        scaling_column_bigger = Column(
            "memUsed", None, None, None, self.measure_type, "kB", None, "1000"
        )
        formatted_value_scaled = scaling_column_bigger.format_value(
            "12.3", *self.default_optionals
        )
        self.assertEqual(formatted_value_scaled, "12300")

    def test_column_init_error_on_missing_unit(self):
        self.assertRaises(
            TableDefinitionError,
            Column,
            "memUsed",
            None,
            None,
            None,
            self.measure_type,
            None,
            None,
            1000,
        )

    def test_column_init_no_error_on_default_scale(self):
        Column("memUsed", None, None, None, self.measure_type, "B")

    def test_column_init_no_error_on_same_unit_without_scale(self):
        Column("memUsed", None, None, None, self.measure_type, "B", "B", None)

    def check_expected_column_type(self, values, expected_type):
        column = Column("empty_column", None, self.sig_figures, None)
        column.set_column_type_from(values)
        self.assertEqual(
            column.type.type, expected_type, msg=f"Actual type: {column.type}"
        )

    def test_column_type_text_value_starts_with_number(self):
        self.check_expected_column_type([1, 1, 1, 1.1, "1,2,3"], ColumnType.text)

    def test_column_type_integers_is_count(self):
        self.check_expected_column_type([1, 2, 3, 99999], ColumnType.count)

    def test_column_type_integer_strings_is_count(self):
        self.check_expected_column_type(["1", "2", "3", "99999"], ColumnType.count)

    def test_column_type_integers_and_integer_strings_is_count(self):
        self.check_expected_column_type(["1", 2, 3, 99999], ColumnType.count)

    def test_column_type_floats_is_measure(self):
        self.check_expected_column_type([1.1, 2.234], ColumnType.measure)

    def test_column_type_floats_and_integers_is_measure(self):
        self.check_expected_column_type([1, 2.234, 3, 4], ColumnType.measure)

    def test_column_type_float_strings_is_measure(self):
        self.check_expected_column_type(["1.1", "2.234"], ColumnType.measure)

    def test_column_type_floats_and_float_strings_is_measure(self):
        self.check_expected_column_type([1.1, "2.234"], ColumnType.measure)

    def test_column_type_integer_and_nan_is_measure(self):
        self.check_expected_column_type([1, 10, nan], ColumnType.measure)

    def test_column_type_integer_string_and_nan_is_measure(self):
        self.check_expected_column_type(["1", "10", nan], ColumnType.measure)

    def test_column_type_integer_and_inf_is_measure(self):
        self.check_expected_column_type([1, 10, inf], ColumnType.measure)

    def test_column_type_integer_string_and_inf_is_measure(self):
        self.check_expected_column_type(["1", "10", inf], ColumnType.measure)

    def test_column_type_integer_and_negative_inf_is_measure(self):
        self.check_expected_column_type([1, 10, -inf], ColumnType.measure)

    def test_column_type_integer_string_and_negative_inf_is_measure(self):
        self.check_expected_column_type(["1", "10", -inf], ColumnType.measure)

    def test_column_type_float_and_nan_is_measure(self):
        self.check_expected_column_type([1.1, 10, nan], ColumnType.measure)

    def test_column_type_float_string_and_nan_is_measure(self):
        self.check_expected_column_type(["1.1", "10.0", nan], ColumnType.measure)

    def test_column_type_float_and_inf_is_measure(self):
        self.check_expected_column_type([1.1, 10, inf], ColumnType.measure)

    def test_column_type_float_string_and_inf_is_measure(self):
        self.check_expected_column_type(["1.1", "10.0", inf], ColumnType.measure)

    def test_column_type_float_and_negative_inf_is_measure(self):
        self.check_expected_column_type([1.1, 10, -inf], ColumnType.measure)

    def test_column_type_float_string_and_negative_inf_is_measure(self):
        self.check_expected_column_type(["1.1", "10.0", -inf], ColumnType.measure)

    def test_column_type_floats_and_text_is_text(self):
        self.check_expected_column_type([1.1, 2.234, "1,2,3"], ColumnType.text)

    def test_column_type_comma_decimal_is_text(self):
        self.check_expected_column_type(["1,2"], ColumnType.text)
