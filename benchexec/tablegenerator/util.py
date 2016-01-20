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

"""
This module contains some useful functions for Strings, Files and Lists.
"""

# prepare for Python 3
from __future__ import absolute_import, division, print_function, unicode_literals

from decimal import Decimal
import glob
import json
import logging
import os

import re
from urllib.parse import quote as url_quote
import tempita

from benchexec import model

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
POSSIBLE_FORMAT_TARGETS = ['html', 'html_cell', 'tooltip_stochastic', 'csv']


def enum(**enums):
    return type('Enum', (), enums)


class ColumnEnumType(object):

    def __init__(self, type, name):
        self._type = type
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
        self.number_of_significant_digits = num_of_digits
        self.type = col_type
        self.unit = unit
        self.scale_factor = float(scale_factor) if scale_factor else 1
        if int(self.scale_factor) == self.scale_factor:
            self.scale_factor = int(self.scale_factor)
        self.href = href


def get_file_list(shortFile):
    """
    The function get_file_list expands a short filename to a sorted list
    of filenames. The short filename can contain variables and wildcards.
    """

    # expand tilde and variables
    expandedFile = os.path.expandvars(os.path.expanduser(shortFile))

    # expand wildcards
    fileList = glob.glob(expandedFile)

    # sort alphabetical,
    # if list is emtpy, sorting returns None, so better do not sort
    if len(fileList) != 0:
        fileList.sort()
    else:
        logging.warning("No file matches '%s'.", shortFile)

    return fileList


def extend_file_list(filelist):
    '''
    This function takes a list of files, expands wildcards
    and returns a new list of files.
    '''
    return [file for wildcardFile in filelist for file in get_file_list(wildcardFile)]


def split_number_and_unit(s):
    """
    Split a string into two parts: a number prefix and an arbitrary suffix.
    Splitting is done from the end, so the split is where the last digit
    in the string is (that means the prefix may include non-digit characters,
    if they are followed by at least one digit).
    """
    if not s:
        return (s, '')
    pos = len(s)
    while pos and not s[pos-1].isdigit():
        pos -= 1
    return (s[:pos], s[pos:])


def remove_unit(s):
    """
    Remove a unit from a number string, or return the full string if it is not a number.
    """
    (prefix, suffix) = split_number_and_unit(s)
    return suffix if prefix == '' else prefix


def create_link(runResult, base_dir, column):
    source_file = runResult.task_id[0]
    href = column.href or runResult.log_file

    if href.startswith("http://") or href.startswith("https://"):
        # quote special characters only in inserted variable values, not full URL
        source_file = url_quote(source_file)
        href = model.substitute_vars([href], None, source_file)[0]
        return href

    # quote special characters everywhere (but not twice in source_file!)
    href = model.substitute_vars([href], None, source_file)[0]
    return url_quote(os.path.relpath(href, base_dir))


def format_options(options):
    '''Helper function for formatting the content of the options line'''
    # split on one of the following tokens: ' -' or '[[' or ']]'
    lines = ['']
    for token in re.split('( -|\[\[|\]\])', options):
      if token in ['[[',']]']:
        lines.append(token)
        lines.append('')
      elif token == ' -':
        lines.append(token)
      else:
        lines[-1] += token
    # join all non-empty lines and wrap them into 'span'-tags
    return '<span style="display:block">' + '</span><span style="display:block">'.join(line for line in lines if line.strip()) + '</span>'


def format_number_align(formattedValue, max_number_of_dec_digits):
    alignment = max_number_of_dec_digits
    if formattedValue.find('.') >= 0:
        # Subtract spaces for digits after the decimal point.
        alignment -= len(formattedValue) - formattedValue.find('.') - 1
    elif max_number_of_dec_digits > 0:
        # Add punctuation space.
        formattedValue += '&#x2008;'
    formattedValue += "".join(['&#x2007;'] * alignment)
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


def format_number(value, number_of_significant_digits, max_digits_after_decimal, isToAlign=False, format_target='html'):
    """
    If the value is a number (or number followed by a unit),
    this function returns a string-representation of the number
    with the specified number of significant digits,
    optionally aligned at the decimal point.

    If the value is not a number, it is returned unchanged.
    """
    if format_target not in POSSIBLE_FORMAT_TARGETS:
        raise ValueError('Unknown format target')

    if value is None:
        return ''

    try:
        # Round to the given amount of significant digits
        #   (unfortunately this keeps the '.0' for large numbers and removes too many zeros from the end).
        float_value = float("{value:.{digits}g}".format(digits=number_of_significant_digits, value=float(value)))
        formatted_value = str(float_value)

        # Get the number of intended significant digits and the number of current significant digits.
        # If we have not enough digits due to rounding, 0's have to be re-added.
        # If we have too many digits due to conversion of integers to float (e.g. 1234.0), the decimals have to be cut
        initial_value_sig_digits = _get_significant_digits(value)
        current_sig_digits = _get_significant_digits(formatted_value)

        intended_digits = min(initial_value_sig_digits, number_of_significant_digits)
        digits_to_add = intended_digits - current_sig_digits

        if digits_to_add > 0:
            assert '.' in formatted_value
            formatted_value += "".join(['0'] * digits_to_add)
        elif digits_to_add < 0:
            assert round(float_value) == float_value  # check that the number has no decimal values
            formatted_value = str(round(float_value))

        # Cut the 0 in front of the decimal point for values < 1.
        # Example: 0.002 => .002
        if format_target == "html_cell" and '.' in formatted_value and 1 > float(formatted_value) >= 0:
            assert formatted_value[0] == '0'
            formatted_value = formatted_value[1:]

        # Alignment
        if isToAlign:
            formatted_value = format_number_align(formatted_value, max_digits_after_decimal)
        return formatted_value
    except ValueError:  # If value is no float, don't format it.
        return value


def format_value(value, column, isToAlign=False, format_target="html"):
    """
    Format a value nicely for human-readable output (including rounding).

    @param value: the value to format
    @param column: a Column object describing the column the value is a part of.
        This given Column is used to derive information about proper formatting.
    @param isToAlign: if True, spaces will be added to the returned String representation to align it to all
        other values in this column, correctly
    @param format_target the target the value should be formatted for
    @return: a formatted String representation of the given value.
    """
    if format_target not in POSSIBLE_FORMAT_TARGETS:
        raise ValueError('Unknown format target')

    if value is None:
        return ''

    if column.type.type == ColumnType.text:
        return value

    # If the number ends with "s" or another unit, remove it.
    # Units should not occur in table cells, but in the table head.
    value = remove_unit(str(value).strip())

    # Apply the scale factor to the value
    try:
        if column.scale_factor != 1:
            value = float(value) * column.scale_factor
            if int(value) == value:
                value = int(value)
            value = str(value)
    except ValueError:
        pass

    number_of_significant_digits = column.number_of_significant_digits
    max_dec_digits = 0
    if number_of_significant_digits is None and format_target is "tooltip_stochastic":
        return str(round(float(value), DEFAULT_TOOLTIP_PRECISION))

    elif column.type.type == ColumnType.measure:
        if number_of_significant_digits is None and format_target is not "csv":
            number_of_significant_digits = DEFAULT_TIME_PRECISION
        max_dec_digits = column.type.max_decimal_digits

    if number_of_significant_digits is not None:
        return format_number(value, int(number_of_significant_digits), int(max_dec_digits), isToAlign, format_target)
    else:
        return value


def to_decimal(s):
    # remove whitespaces and trailing units (e.g., in '1.23s')
    if s:
        s, _ = split_number_and_unit(s.strip())
        return Decimal(s) if s else None
    else:
        return None


def collapse_equal_values(values, counts):
    """
    Take a tuple (values, counts), remove consecutive values and increment their count instead.
    """
    assert len(values) == len(counts)
    previousValue = values[0]
    previousCount = 0

    for value, count in zip(values, counts):
        if value != previousValue:
            yield (previousValue, previousCount)
            previousCount = 0
            previousValue = value
        previousCount += count

    yield (previousValue, previousCount)


def get_column_value(sourcefileTag, columnTitle, default=None):
    for column in sourcefileTag.findall('column'):
        if column.get('title') == columnTitle:
                return column.get('value')
    return default


def flatten(list_):
    return [value for sublist in list_ for value in sublist]


def to_json(obj):
    return tempita.html(json.dumps(obj, sort_keys=True))


def prettylist(list_):
    if not list_:
        return ''

    # Filter out duplicate values while keeping order
    values = set()
    uniqueList = []
    for entry in list_:
        if not entry in values:
            values.add(entry)
            uniqueList.append(entry)

    return uniqueList[0] if len(uniqueList) == 1 \
        else '[' + '; '.join(uniqueList) + ']'
