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

from benchexec.tablegenerator import util


class FormatValueTests(unittest.TestCase):

    def setUp(self):        
        self.max_dec_digits = 6
        self.sig_figures = 4
        self.measure_type = util.ColumnMeasureType(self.max_dec_digits)
        self.measure_column = util.Column("CpuTime", None, self.sig_figures, None, self.measure_type, None, 1)
        self.default_optionals = (False, 'html')

    def tearDown(self):
        pass
    
    def test_format_value_none(self):
        formatted_value_none = util.format_value(None, self.measure_column, *self.default_optionals)
        self.assertEqual(formatted_value_none, '')

    def test_format_value_no_align(self):
        formatted_value_no_align = util.format_value("1.555s", self.measure_column, *self.default_optionals)
        self.assertEqual(formatted_value_no_align,   "1.555")

    def test_format_value_no_align_rounded(self):
        formatted_value_no_align_rounded = util.format_value("0.55559", self.measure_column, *self.default_optionals)
        self.assertEqual(formatted_value_no_align_rounded,   "0.5556")

    def test_format_value_add_missing_zeros(self):
        formatted_value_no_align_zeros_cut = util.format_value("9.599999", self.measure_column, *self.default_optionals)
        self.assertEqual(formatted_value_no_align_zeros_cut,   "9.600")

    def test_format_value_align_decimal(self):
        formatted_value_aligned = util.format_value("1.555s", self.measure_column, True, 'html')
        self.assertEqual(formatted_value_aligned,   "1.555&#x2007;&#x2007;&#x2007;")

    def test_format_value_align_int(self):
        formatted_value_int_aligned = util.format_value("20", self.measure_column, True, 'html')
        self.assertEqual(formatted_value_int_aligned,   "20&#x2008;&#x2007;&#x2007;&#x2007;&#x2007;&#x2007;&#x2007;")

    def test_format_value_cut_0_at_front(self):
        formatted_value_0_cut = util.format_value("0.055999", self.measure_column, True, 'html_cell')
        self.assertEqual(formatted_value_0_cut,    ".05600&#x2007;")

    def test_format_value_two_significant_figures(self):
        self.measure_column_two_sig_figures = util.Column("CpuTime", None, 2, None, self.measure_type, None, 1)
        formatted_value_decimals_cut = util.format_value("9.99999", self.measure_column_two_sig_figures, *self.default_optionals)
        self.assertEqual(formatted_value_decimals_cut,   "10")

    def test_format_value_no_sigs(self):
        self.measure_column_no_sigs = util.Column("CpuTime", None, None, None, self.measure_type, None, 1)
        formatted_value_rounding = util.format_value("9999.12015s", self.measure_column_no_sigs, *self.default_optionals)
        self.assertEqual(formatted_value_rounding,   "10000")

    def test_format_value_tooltip_explicit_sigs(self):
        formatted_value_tooltip_considers_explicit_sigs = util.format_value("9999.125s", self.measure_column, None, 'tooltip_stochastic')
        self.assertEqual(formatted_value_tooltip_considers_explicit_sigs,   "9999")

    def test_format_value_tooltip_explicit_sigs2(self):
        formatted_value_tooltip_considers_explicit_sigs = util.format_value("0.125s", self.measure_column, None, 'tooltip_stochastic')
        self.assertEqual(formatted_value_tooltip_considers_explicit_sigs,   "0.125")

    def test_format_value_tooltip_explicit_sigs3(self):
        formatted_value_tooltip_considers_explicit_sigs = util.format_value("0.125999s", self.measure_column, None, 'tooltip_stochastic')
        self.assertEqual(formatted_value_tooltip_considers_explicit_sigs,   "0.1260")

    def test_format_value_count_alignment(self):
        count_column = util.Column("memUsed", None, None, None, util.ColumnType.count, None, 1)
        formatted_value_count_no_align_no_sigs = util.format_value("123456789", count_column, *self.default_optionals)
        self.assertEqual(formatted_value_count_no_align_no_sigs,   "123456789")

        formatted_value_aligned = util.format_value("123456789", count_column, True, 'html_cell')
        self.assertEqual(formatted_value_aligned, formatted_value_count_no_align_no_sigs)

    def test_format_value_count_sigs(self):
        count_column_sigs = util.Column("memUsed", None, 3, None, util.ColumnType.count, None, 1)
        formatted_value_count_sigs = util.format_value("123456789", count_column_sigs, *self.default_optionals)
        self.assertEqual(formatted_value_count_sigs,   "123000000")

    def test_format_value_scale_values_down(self):
        scaling_column_smaller = util.Column("memUsed", None, None, None, self.measure_type, None, '0.0000001')
        formatted_value_scaled = util.format_value("123456789", scaling_column_smaller, *self.default_optionals)
        self.assertEqual(formatted_value_scaled, "12.3")

    def test_format_value_scale_values_up(self):
        scaling_column_bigger = util.Column("memUsed", None, None, None, self.measure_type, None, '1000')
        formatted_value_scaled = util.format_value("12.3", scaling_column_bigger, *self.default_optionals)
        self.assertEqual(formatted_value_scaled, "12300")
