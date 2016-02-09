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

import re
import math

from benchexec.tablegenerator import util

__all__ = ['Column, ColumnType, ColumnMeasureType']


DEFAULT_TIME_PRECISION = 3
DEFAULT_TOOLTIP_PRECISION = 2
REGEX_SIGNIFICANT_DIGITS = re.compile('([-\+])?(\d+)\.?(0*(\d+))?([eE]([-\+])(\d+))?')  # compile regular expression only once for later uses
GROUP_SIGN = 1
GROUP_INT_PART = 2
GROUP_DEC_PART = 3
GROUP_SIG_DEC_DIGITS = 4
GROUP_EXP = 5
GROUP_EXP_SIGN = 6
GROUP_EXP_VAL = 7
POSSIBLE_FORMAT_TARGETS = ['html', 'html_cell', 'tooltip', 'tooltip_stochastic', 'csv']

def enum(**enums):
    return type('Enum', (), enums)


class ColumnEnumType(object):

    def __init__(self, _type, name):
        self._type = _type
        self.name = name

    @property
    def type(self):
        return self

    def __str__(self):
        return self.name

    def __eq__(self, other):
        try:
            return self._type == other._type
        except:
            return False


class ColumnType(object):
    column_types = enum(text=1, count=2, measure=3, status=4, main_status=5)
    text = ColumnEnumType(column_types.text, 'text')
    count = ColumnEnumType(column_types.count, 'count')
    measure = ColumnEnumType(column_types.measure, 'measure')
    status = ColumnEnumType(column_types.status, 'status')
    main_status = ColumnEnumType(column_types.main_status, 'main_status')


class ColumnMeasureType(object):
    """
    Column type 'Measure', contains the column's unit and the largest amount of digits after the decimal point.
    """
    def __init__(self, max_decimal_digits):
        self._type = ColumnType.measure
        self._max_decimal_digits = max_decimal_digits

    @property
    def type(self):
        return self._type

    @property
    def max_decimal_digits(self):
        return self._max_decimal_digits


class Column(object):
    """
    The class Column contains title, pattern (to identify a line in log_file),
    number_of_significant_digits of a column, the type of the column's values,
    their unit, a scale factor to apply to all values of the column (mostly to fit the unit)
    and href (to create a link to a resource).
    It does NOT contain the value of a column.
    """
    def __init__(self, title, pattern, num_of_digits, href, col_type=None, unit=None, scale_factor=1):
        self.title = title
        self.pattern = pattern
        self.number_of_significant_digits = int(num_of_digits) if num_of_digits else None
        self.type = col_type
        self.unit = unit
        self.scale_factor = float(scale_factor) if scale_factor else 1
        self.href = href

    def is_numeric(self):
        return self.type.type == ColumnType.measure or self.type.type == ColumnType.count

    def format_title(self):
        if self.is_numeric() and self.unit:
            return "{} ({})".format(self.title, self.unit)
        else:
            return self.title

    def format_value(self, value, isToAlign=False, format_target="html"):
        """
        Format a value nicely for human-readable output (including rounding).

        @param value: the value to format
        @param isToAlign: if True, spaces will be added to the returned String representation to align it to all
            other values in this column, correctly
        @param format_target the target the value should be formatted for
        @return: a formatted String representation of the given value.
        """
        if format_target not in POSSIBLE_FORMAT_TARGETS:
            raise ValueError('Unknown format target')

        if value is None:
            return ''

        # If the number ends with "s" or another unit, remove it.
        # Units should not occur in table cells, but in the table head.
        number_str = util.remove_unit(str(value).strip())

        try:
            number = float(number_str)
        except ValueError:  # If value is no float, don't format it.
            return value

        # Apply the scale factor to the value
        number = number * self.scale_factor

        number_of_significant_digits = self.number_of_significant_digits
        max_dec_digits = 0
        if number_of_significant_digits is None and format_target is "tooltip_stochastic":
            return str(round(number, DEFAULT_TOOLTIP_PRECISION))

        elif self.type.type == ColumnType.measure:
            if number_of_significant_digits is None and format_target is not "csv":
                number_of_significant_digits = DEFAULT_TIME_PRECISION
            max_dec_digits = self.type.max_decimal_digits

        if number_of_significant_digits is not None:
            current_significant_digits = _get_significant_digits(number_str)
            return _format_number(number, current_significant_digits, number_of_significant_digits, max_dec_digits, isToAlign, format_target)
        else:
            if number == float(number_str):
                # TODO remove as soon as scaled values are handled correctly
                return number_str
            if int(number) == number:
                number = int(number)
            return str(number)


def _format_number_align(formattedValue, max_number_of_dec_digits, format_target="html"):
    alignment = max_number_of_dec_digits

    if formattedValue.find('.') >= 0:
        # Subtract spaces for digits after the decimal point.
        alignment -= len(formattedValue) - formattedValue.find('.') - 1
    elif max_number_of_dec_digits > 0 and format_target.startswith('html'):
        # Add punctuation space.
        formattedValue += '&#x2008;'

    if format_target.startswith('html'):
        whitespace = '&#x2007;'
    else:
        whitespace = ' '
    formattedValue += whitespace * alignment

    return formattedValue


def _get_significant_digits(value):
    # Regular expression returns multiple groups:
    #
    # Group GROUP_SIGN: Optional sign of value
    # Group GROUP_INT_PART: Digits in front of decimal point
    # Group GROUP_DEC_PART: Optional digits after decimal point
    # Group GROUP_SIG_DEC_DIGITS: Digits after decimal point, starting at the first value not 0
    # Group GROUP_EXP: Optional exponent part (e.g. 'e-5')
    # Group GROUP_EXP_SIGN: Optional sign of exponent part
    # Group GROUP_EXP_VALUE: Value of exponent part (e.g. '5' for 'e-5')
    # Use these groups to compute the number of zeros that have to be added to the current number's
    # decimal positions.
    match = REGEX_SIGNIFICANT_DIGITS.match(value)

    if int(match.group(GROUP_INT_PART)) == 0 and float(value) != 0:
        sig_digits = len(match.group(GROUP_SIG_DEC_DIGITS))

    else:
        sig_digits = len(match.group(GROUP_INT_PART))
        if match.group(GROUP_DEC_PART):
            sig_digits += len(match.group(GROUP_DEC_PART))

    return sig_digits


def _format_number(number, initial_value_sig_digits, number_of_significant_digits, max_digits_after_decimal, isToAlign, format_target):
    """
    If the value is a number (or number followed by a unit),
    this function returns a string-representation of the number
    with the specified number of significant digits,
    optionally aligned at the decimal point.
    """
    assert format_target in POSSIBLE_FORMAT_TARGETS

    # Round to the given amount of significant digits
    intended_digits = min(initial_value_sig_digits, number_of_significant_digits)
    if number == 0:
        float_value = 0
    else:
        float_value = round(number, - int(math.floor(math.log10(number))) + (number_of_significant_digits - 1))

    if not format_target.startswith('tooltip'):
        max_digits_to_display = max_digits_after_decimal
    else:
        max_digits_to_display = len(str(float_value))  # This value may be too big, but extra digits will be cut below
    formatted_value = "{0:.{1}f}".format(float_value, max_digits_to_display)

    # Get the number of intended significant digits and the number of current significant digits.
    # If we have not enough digits due to rounding, 0's have to be re-added.
    # If we have too many digits due to conversion of integers to float (e.g. 1234.0), the decimals have to be cut
    current_sig_digits = _get_significant_digits(formatted_value)

    digits_to_add = intended_digits - current_sig_digits

    if digits_to_add > 0:
        assert '.' in formatted_value
        formatted_value += "".join(['0'] * digits_to_add)
    elif digits_to_add < 0:
        if '.' in formatted_value[:digits_to_add]:
            formatted_value = formatted_value[:digits_to_add]
        else:
            formatted_value = str(round(float_value))

        if formatted_value.endswith('.'):
            formatted_value = formatted_value[:-1]

    # Cut the 0 in front of the decimal point for values < 1.
    # Example: 0.002 => .002
    if _is_to_cut(formatted_value, format_target, isToAlign):
        assert formatted_value[0] == '0'
        formatted_value = formatted_value[1:]

    # Alignment
    if isToAlign:
        formatted_value = _format_number_align(formatted_value, max_digits_after_decimal, format_target)
    return formatted_value


def _is_to_cut(value, format_target, is_to_align):
    correct_target = format_target == "html_cell" or (format_target == 'csv' and is_to_align)

    return correct_target and '.' in value and 1 > float(value) >= 0
