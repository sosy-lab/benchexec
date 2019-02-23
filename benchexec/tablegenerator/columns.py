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
from math import floor, ceil, log10, isnan, isinf
import logging

from benchexec.tablegenerator import util

__all__ = ['Column, ColumnType, ColumnMeasureType, get_column_type']

DEFAULT_TIME_PRECISION = 3
DEFAULT_TOOLTIP_PRECISION = 2
# Compile regular expression for detecting measurements only once.
REGEX_MEASURE = re.compile(r'\s*([-\+])?(?:([Nn][aA][Nn]|[iI][nN][fF])|(\d+)(\.(0*)(\d+))?([eE]([-\+])(\d+))?\s?([a-zA-Z/%]*))\s*$')
GROUP_SIGN = 1
GROUP_SPECIAL_FLOATS_PART = 2
GROUP_INT_PART = 3
GROUP_DEC_PART = 4
GROUP_ZEROES = 5
GROUP_SIG_DEC_PART = 6
GROUP_EXPONENT_PART = 7
GROUP_EXPONENT_SIGN = 8
GROUP_EXPONENT_VALUE = 9
GROUP_UNIT = 10
POSSIBLE_FORMAT_TARGETS = ['html', 'html_cell', 'tooltip', 'tooltip_stochastic', 'csv']

DEFAULT_NUMBER_OF_SIGNIFICANT_DIGITS = 3

UNIT_CONVERSION = {
    's': {'ms': 1000, 'min': 1.0 / 60, 'h': 1.0 / 3600},
    'B': {'kB': 1.0 / 10 ** 3, 'MB': 1.0 / 10 ** 6, 'GB': 1.0 / 10 ** 9},
    'J': {'kJ': 1.0 / 10 ** 3, 'Ws': 1, 'kWs': 1.0 / 1000,
          'Wh': 1.0 / 3600, 'kWh': 1.0 / (1000 * 3600), 'mWh': 1.0 / (1000 * 1000 * 3600)}
}

inf = float('inf')


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

    def __str__(self):
        return "{}({})".format(self._type, self._max_decimal_digits)


class Column(object):
    """
    The class Column contains title, pattern (to identify a line in log_file),
    number_of_significant_digits of a column, the type of the column's values,
    their unit, a scale factor to apply to all values of the column (mostly to fit the unit)
    and href (to create a link to a resource).
    It does NOT contain the value of a column.

    The following conditions must be kept, but cannot be checked in the constructor.
    If they are violated, they may lead to errors in other parts of the program.
    * If 'scale_factor' is a value other than the default, 'unit' must be set.
    * If 'unit' and 'scale_factor' are set, 'source_unit' must be set, or the column's cells must not have a
      source unit, i.e. the source unit "".
    * If set, 'source_unit' must fit the source unit of the column's cells.
    * In addition, if 'unit' and 'source_unit' are set and of different values,
      'scale_factor' must be a value other than 'None'.
    """

    def __init__(self, title, pattern, num_of_digits, href, col_type=None,
                 unit=None, source_unit=None, scale_factor=None, relevant_for_diff=None, display_title=None):

        # If scaling on the variables is performed, a display unit must be defined, explicitly
        if scale_factor is not None and scale_factor != 1 and unit is None:
            raise util.TableDefinitionError("Scale factor is defined, but display unit is not (in column {})"
                                            .format(title))

        self.title = title
        self.pattern = pattern
        self.number_of_significant_digits = int(num_of_digits) if num_of_digits else None
        self.type = col_type
        self.unit = unit
        self.source_unit = source_unit
        self.scale_factor = float(scale_factor) if scale_factor else scale_factor
        self.href = href
        if relevant_for_diff is None:
            self.relevant_for_diff = False
        else:
            self.relevant_for_diff = True \
                if relevant_for_diff.lower() == "true" else False
        self.display_title = display_title

    def is_numeric(self):
        return self.type.type == ColumnType.measure or self.type.type == ColumnType.count

    def format_title(self):
        title = self.display_title or self.title
        if self.is_numeric() and (self.unit or self.source_unit):
            used_unit = self.unit or self.source_unit
            return "{} ({})".format(title, used_unit)

        else:
            return title

    def format_value(self, value, isToAlign=False, format_target="html"):
        """
        Format a value nicely for human-readable output (including rounding).

        @param value: the value to format
        @param isToAlign: if True, spaces will be added to the returned String representation to align it to all
            other values in this column, correctly
        @param format_target the target the value should be formatted for
        @return: a formatted String representation of the given value.
        """
        # Only format counts and measures
        if self.type.type != ColumnType.count and self.type.type != ColumnType.measure:
            return value

        if format_target not in POSSIBLE_FORMAT_TARGETS:
            raise ValueError('Unknown format target')

        if value is None or value == '':
            return ''

        # If the number ends with "s" or another unit, remove it.
        # Units should not occur in table cells, but in the table head.
        number_str = util.remove_unit(str(value).strip())
        number = float(number_str)

        if isnan(number):
            return 'NaN'
        elif number == inf:
            return 'Inf'
        elif number == -inf:
            return '-Inf'

        # Apply the scale factor to the value
        if self.scale_factor is not None:
            number *= self.scale_factor

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
            return _format_number(number, current_significant_digits, number_of_significant_digits, max_dec_digits,
                                  isToAlign, format_target)
        else:
            if number == float(number_str) or isnan(number) or isinf(number):
                # TODO remove as soon as scaled values are handled correctly
                return number_str
            if int(number) == number:
                number = int(number)
            return str(number)

    def __str__(self):
        return "{}(title={}, pattern={}, num_of_digits={}, href={}, col_type={}, unit={}, scale_factor={})".format(
            self.__class__.__name__, self.title, self.pattern, self.number_of_significant_digits, self.href, self.type,
            self.unit, self.scale_factor)


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
    if isnan(float(value)) or isinf(float(value)):
        return 0

    # Regular expression returns multiple groups:
    #
    # Group GROUP_SIGN: Optional sign of value
    # Group GROUP_INT_PART: Digits in front of decimal point
    # Group GROUP_DEC_PART: Optional decimal point and digits after it
    # Group GROUP_SIG_DEC_DIGITS: Digits after decimal point, starting at the first value not 0
    # Group GROUP_EXP: Optional exponent part (e.g. 'e-5')
    # Group GROUP_EXP_SIGN: Optional sign of exponent part
    # Group GROUP_EXP_VALUE: Value of exponent part (e.g. '5' for 'e-5')
    # Use these groups to compute the number of zeros that have to be added to the current number's
    # decimal positions.
    match = REGEX_MEASURE.match(value)

    if int(match.group(GROUP_INT_PART)) == 0 and float(value) != 0:
        sig_digits = len(match.group(GROUP_SIG_DEC_PART))

    else:
        if float(value) != 0:
            sig_digits = len(match.group(GROUP_INT_PART))
        else:
            # If the value consists of only zeros, do not count the 0 in front of the decimal
            sig_digits = 0
        if match.group(GROUP_DEC_PART):
            sig_digits += len(match.group(GROUP_DEC_PART)) - 1  # -1 for the decimal point

    return sig_digits


def _format_number(number, initial_value_sig_digits, number_of_significant_digits, max_digits_after_decimal, isToAlign,
                   format_target):
    """
    If the value is a number (or number followed by a unit),
    this function returns a string-representation of the number
    with the specified number of significant digits,
    optionally aligned at the decimal point.
    """
    assert format_target in POSSIBLE_FORMAT_TARGETS, "Invalid format " + format_target

    # Round to the given amount of significant digits
    intended_digits = min(initial_value_sig_digits, number_of_significant_digits)
    if number == 0:
        formatted_value = '0'
        if max_digits_after_decimal > 0 and initial_value_sig_digits > 0:
            formatted_value += '.' + '0' * min(max_digits_after_decimal, initial_value_sig_digits)

    else:
        float_value = round(number, - int(floor(log10(abs(number)))) + (number_of_significant_digits - 1))

        if not format_target.startswith('tooltip'):
            max_digits_to_display = max_digits_after_decimal
        else:
            max_digits_to_display = len(
                str(float_value))  # This value may be too big, but extra digits will be cut below
        formatted_value = "{0:.{1}f}".format(float_value, max_digits_to_display)

        # Get the number of intended significant digits and the number of current significant digits.
        # If we have not enough digits due to rounding, 0's have to be re-added.
        # If we have too many digits due to conversion of integers to float (e.g. 1234.0), the decimals have to be cut
        current_sig_digits = _get_significant_digits(formatted_value)

        digits_to_add = intended_digits - current_sig_digits

        if digits_to_add > 0:
            if '.' not in formatted_value:
                raise AssertionError(
                    "Unexpected string '{}' after rounding '{}' to '{}' with {} significant digits and {} decimal digits for format '{}'"
                        .format(formatted_value, number, float_value, intended_digits, max_digits_to_display,
                                format_target))
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


def get_column_type(column, column_values):
    """
    Returns the type of the given column based on its row values on the given RunSetResult.
    @param column: the column to return the correct ColumnType for
    @param column_values: the column values to consider
    @return: a tuple of a type object describing the column - the concrete ColumnType is stored in the attribute 'type',
        the display unit of the column, which may be None,
        the source unit of the column, which may be None,
        and the scale factor to convert from the source unit to the display unit.
        If no scaling is necessary for conversion, this value is 1.
    """

    try:
        return _get_column_type_heur(column, column_values)
    except util.TableDefinitionError as e:
        logging.error("Column type couldn't be determined: {}".format(e.message))
        return ColumnType.text, None, None, 1


def _get_column_type_heur(column, column_values):
    text_type_tuple = ColumnType.text, None, None, 1

    if "status" in column.title:
        if column.title == "status":
            return ColumnType.main_status, None, None, 1
        else:
            return ColumnType.status, None, None, 1

    column_type = column.type or None
    if column_type and column_type.type == ColumnType.measure:
        column_type = ColumnMeasureType(0)
    column_unit = column.unit  # May be None
    column_source_unit = column.source_unit  # May be None
    column_scale_factor = column.scale_factor  # May be None

    if column_unit:
        explicit_unit_defined = True
    else:
        explicit_unit_defined = False

    if column_scale_factor is None:
        explicit_scale_defined = False
    else:
        explicit_scale_defined = True

    for value in column_values:

        if value is None or value == '':
            continue

        value_match = REGEX_MEASURE.match(str(value))

        # As soon as one row's value is no number, the column type is 'text'
        if value_match is None:
            return text_type_tuple
        else:
            curr_column_unit = value_match.group(GROUP_UNIT)

            # If the units in two different rows of the same column differ,
            # 1. Raise an error if an explicit unit is defined by the displayUnit attribute
            #    and the unit in the column cell differs from the defined sourceUnit, or
            # 2. Handle the column as 'text' type, if no displayUnit was defined for the column's values.
            #    In that case, a unit different from the definition of sourceUnit does not lead to an error.
            if curr_column_unit:
                if column_source_unit is None and not explicit_scale_defined:
                    column_source_unit = curr_column_unit
                elif column_source_unit != curr_column_unit:
                    raise util.TableDefinitionError(
                        "Attribute sourceUnit different from real source unit: {} and {} (in column {})"
                            .format(column_source_unit, curr_column_unit, column.title))
                if column_unit and curr_column_unit != column_unit:
                    if explicit_unit_defined:
                        _check_unit_consistency(curr_column_unit, column_source_unit, column)
                    else:
                        return text_type_tuple
                else:
                    column_unit = curr_column_unit

            if column_scale_factor is None:
                column_scale_factor = _get_scale_factor(column_unit, column_source_unit, column)

            # Compute the number of decimal digits of the current value, considering the number of significant
            # digits for this column.
            # Use the column's scale factor for computing the decimal digits of the current value.
            # Otherwise, they might be different from output.
            scaled_value = float(util.remove_unit(str(value))) * column_scale_factor

            # Due to the scaling operation above, floats in the exponent notation may be created. Since this creates
            # special cases, immediately convert the value back to decimal notation.
            if value_match.group(GROUP_DEC_PART):
                dec_digits_before_scale = len(
                    value_match.group(GROUP_DEC_PART)) - 1  # - 1 since GROUP_DEC_PART includes the point
            else:
                dec_digits_before_scale = 0
            max_number_of_dec_digits_after_scale = max(0, dec_digits_before_scale - ceil(log10(column_scale_factor)))

            scaled_value = "{0:.{1}f}".format(scaled_value, max_number_of_dec_digits_after_scale)
            scaled_value_match = REGEX_MEASURE.match(scaled_value)

            curr_dec_digits = _get_decimal_digits(scaled_value_match, column.number_of_significant_digits)

            try:
                max_dec_digits = column_type.max_decimal_digits
            except AttributeError or TypeError:
                max_dec_digits = 0

            if curr_dec_digits > max_dec_digits:
                max_dec_digits = curr_dec_digits

            if (column_type and column_type.type == ColumnType.measure) or \
                    scaled_value_match.group(GROUP_DEC_PART) is not None or \
                    value_match.group(GROUP_DEC_PART) is not None or \
                    scaled_value_match.group(GROUP_SPECIAL_FLOATS_PART) is not None:
                column_type = ColumnMeasureType(max_dec_digits)

            elif int(column_scale_factor) != column_scale_factor:
                column_type = ColumnMeasureType(0)
            else:
                column_type = ColumnType.count

    if column_type:
        return column_type, column_unit, column_source_unit, column_scale_factor
    else:
        return text_type_tuple


# This function assumes that scale_factor is not defined.
# Because of this, an error is raised if unit is defined, different from the source_unit, and
# no conversion for these two units is known.
# (Since a scale_factor must be given explicitly, then)
def _get_scale_factor(unit, source_unit, column):
    if unit is None or unit == source_unit:
        return 1
    elif source_unit in UNIT_CONVERSION.keys() and unit in UNIT_CONVERSION[source_unit].keys():
        return UNIT_CONVERSION[source_unit][unit]
    else:
        # If the display unit is different from the source unit, a scale factor must be given explicitly
        raise util.TableDefinitionError("Attribute displayUnit is different from sourceUnit," +
                                        " but scaleFactor is not defined (in column {})"
                                        .format(column.title))


def _get_decimal_digits(decimal_number_match, number_of_significant_digits):
    """
    Returns the amount of decimal digits of the given regex match, considering the number of significant
    digits for the provided column.

    @param decimal_number_match: a regex match of a decimal number, resulting from REGEX_MEASURE.match(x).
    @param number_of_significant_digits: the number of significant digits required
    @return: the number of decimal digits of the given decimal number match's representation, after expanding
        the number to the required amount of significant digits
    """

    assert 'e' not in decimal_number_match.group()  # check that only decimal notation is used

    try:
        num_of_digits = int(number_of_significant_digits)
    except TypeError:
        num_of_digits = DEFAULT_NUMBER_OF_SIGNIFICANT_DIGITS

    if not decimal_number_match.group(GROUP_DEC_PART):
        return 0

    # If 1 > value > 0, only look at the decimal digits.
    # In the second condition, we have to remove the first character from the decimal part group because the
    # first character always is '.'
    if int(decimal_number_match.group(GROUP_INT_PART)) == 0 \
            and int(decimal_number_match.group(GROUP_DEC_PART)[1:]) != 0:

        max_num_of_digits = len(decimal_number_match.group(GROUP_SIG_DEC_PART))
        num_of_digits = min(num_of_digits, max_num_of_digits)
        # number of needed decimal digits = number of zeroes after decimal point + significant digits
        curr_dec_digits = len(decimal_number_match.group(GROUP_ZEROES)) + int(num_of_digits)

    else:
        max_num_of_digits = \
            len(decimal_number_match.group(GROUP_INT_PART)) + len(decimal_number_match.group(GROUP_DEC_PART))
        num_of_digits = min(num_of_digits, max_num_of_digits)
        # number of needed decimal digits = significant digits - number of digits in front of decimal point
        curr_dec_digits = int(num_of_digits) - len(decimal_number_match.group(GROUP_INT_PART))

    return curr_dec_digits


def _check_unit_consistency(actual_unit, wanted_unit, column):
    if actual_unit and wanted_unit is None:
        raise util.TableDefinitionError("Trying to convert from one unit to another, but source unit not specified"
                                        " (in column {})".format(column.title))
    elif wanted_unit != actual_unit:
        raise util.TableDefinitionError("Source value of different unit than specified source unit: " +
                                        "{} and {}"
                                        " (in column {})".format(actual_unit, wanted_unit, column.title))
