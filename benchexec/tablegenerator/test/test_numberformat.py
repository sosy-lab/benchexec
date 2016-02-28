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

import unittest

from benchexec.tablegenerator.columns import Column, ColumnType, ColumnMeasureType


class FormatValueTests(unittest.TestCase):

    def setUp(self):
        self.max_dec_digits = 6
        self.sig_figures = 4
        self.measure_type = ColumnMeasureType(self.max_dec_digits)
        self.measure_column = Column("CpuTime", None, self.sig_figures, None, self.measure_type, None, 1)
        self.default_optionals = (False, 'html')

    def tearDown(self):
        pass

    def test_format_value_none(self):
        formatted_value_none = self.measure_column.format_value(None, *self.default_optionals)
        self.assertEqual(formatted_value_none, '')

    def test_format_value_no_align(self):
        formatted_value_no_align = self.measure_column.format_value("1.555s", *self.default_optionals)
        self.assertEqual(formatted_value_no_align,   "1.555")

    def test_format_value_no_align_rounded(self):
        formatted_value_no_align_rounded = self.measure_column.format_value("0.55559", *self.default_optionals)
        self.assertEqual(formatted_value_no_align_rounded,   "0.5556")

    def test_format_value_add_missing_zeros(self):
        formatted_value_no_align_zeros_cut = self.measure_column.format_value("9.599999", *self.default_optionals)
        self.assertEqual(formatted_value_no_align_zeros_cut,   "9.600")

    def test_format_value_align_decimal(self):
        formatted_value_aligned = self.measure_column.format_value("1.555s", True, 'html')
        self.assertEqual(formatted_value_aligned,   "1.555&#x2007;&#x2007;&#x2007;")

    def test_format_value_small_value(self):
        small_value = "0.000008767"
        small_value_measure_type = ColumnMeasureType(len(small_value) - 3)
        small_value_column = Column("CpuTime", None, 3, None, small_value_measure_type, unit=None, scale_factor=1)
        formatted_value_aligned = small_value_column.format_value(small_value, True, 'html')
        self.assertEqual(formatted_value_aligned, "0.00000877")

        # Test whether scaling to small values and resulting values are handled correctly
        small_value_measure_type = ColumnMeasureType(12)
        small_value_column = Column("CpuTime", None, 3, None, small_value_measure_type, unit=None, scale_factor=1e-10)
        formatted_value_aligned = small_value_column.format_value('2', True, 'html')
        self.assertEqual(formatted_value_aligned, '0.0000000002&#x2007;&#x2007;')

    def test_format_value_align_int(self):
        formatted_value_int_aligned = self.measure_column.format_value("20", True, 'html')
        self.assertEqual(formatted_value_int_aligned,   "20&#x2008;&#x2007;&#x2007;&#x2007;&#x2007;&#x2007;&#x2007;")

    def test_format_value_cut_0_at_front(self):
        formatted_value_0_cut = self.measure_column.format_value("0.055999", True, 'html_cell')
        self.assertEqual(formatted_value_0_cut,    ".05600&#x2007;")

    def test_format_value_two_significant_figures(self):
        self.measure_column_two_sig_figures = Column("CpuTime", None, 2, None, self.measure_type, None, 1)
        formatted_value_decimals_cut = self.measure_column_two_sig_figures.format_value("9.99999", *self.default_optionals)
        self.assertEqual(formatted_value_decimals_cut,   "10")

    def test_format_value_no_sigs(self):
        self.measure_column_no_sigs = Column("CpuTime", None, None, None, self.measure_type, None, 1)
        formatted_value_rounding = self.measure_column_no_sigs.format_value("9999.12015s", *self.default_optionals)
        self.assertEqual(formatted_value_rounding,   "10000")

    def test_format_value_tooltip_explicit_sigs(self):
        formatted_value_tooltip_considers_explicit_sigs = self.measure_column.format_value("9999.125s", None, 'tooltip_stochastic')
        self.assertEqual(formatted_value_tooltip_considers_explicit_sigs,   "9999")

    def test_format_value_tooltip_explicit_sigs2(self):
        formatted_value_tooltip_considers_explicit_sigs = self.measure_column.format_value("0.125s", None, 'tooltip_stochastic')
        self.assertEqual(formatted_value_tooltip_considers_explicit_sigs,   "0.125")

    def test_format_value_tooltip_explicit_sigs3(self):
        formatted_value_tooltip_considers_explicit_sigs = self.measure_column.format_value("0.125999s", None, 'tooltip_stochastic')
        self.assertEqual(formatted_value_tooltip_considers_explicit_sigs,   "0.1260")

    def test_format_value_count_alignment(self):
        count_column = Column("memUsed", None, None, None, ColumnType.count, None, 1)
        formatted_value_count_no_align_no_sigs = count_column.format_value("123456789", *self.default_optionals)
        self.assertEqual(formatted_value_count_no_align_no_sigs,   "123456789")

        formatted_value_aligned = count_column.format_value("123456789", True, 'html_cell')
        self.assertEqual(formatted_value_aligned, formatted_value_count_no_align_no_sigs)

    def test_format_value_count_sigs(self):
        count_column_sigs = Column("memUsed", None, 3, None, ColumnType.count, None, 1)
        formatted_value_count_sigs = count_column_sigs.format_value("123456789", *self.default_optionals)
        self.assertEqual(formatted_value_count_sigs,   "123000000")

    def test_format_value_scale_values_down(self):
        scaling_column_smaller = Column("memUsed", None, None, None, self.measure_type, None, '0.0000001')
        formatted_value_scaled = scaling_column_smaller.format_value("123456789", *self.default_optionals)
        self.assertEqual(formatted_value_scaled, "12.3")

    def test_format_value_scale_values_up(self):
        scaling_column_bigger = Column("memUsed", None, None, None, self.measure_type, None, '1000')
        formatted_value_scaled = scaling_column_bigger.format_value("12.3", *self.default_optionals)
        self.assertEqual(formatted_value_scaled, "12300")
