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
from enum import Enum

import re
import tempita

DEFAULT_TIME_PRECISION = 3
REGEX_SIGNIFICANT_DIGITS = re.compile('(\d+)\.?(0*(\d+))')

class ColumnType(Enum):
    text = 1
    count = 2
    measure = 3

    def get_type(self):
        return self

class ColumnMeasureType(object):
    """
    Column type 'Measure', contains the column's largest amount of digits after the decimal point.
    """
    def __init__(self, max_decimal_digits):
        self.max_decimal_digits = max_decimal_digits

    def get_type(self):
        return ColumnType.measure


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
    from os.path import relpath, join
    from benchexec import model 
    if not column.href:
        return relpath(runResult.log_file, base_dir)
    source_file = runResult.task_id[0]
    href = model.substitute_vars([column.href], None, source_file)[0]
    if href.startswith('http://'):
        return href
    return join(base_dir, href)

def format_options(options):
    '''Helper function for formatting the content of the options line'''
    # split on one of the following tokens: ' -' or '[[' or ']]'
    lines = ['']
    import re
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
    else:
        # Add punctuation space.
        formattedValue += '&#x2008;'
    formattedValue += "".join(['&#x2007;'] * alignment)
    return formattedValue

def format_number(s, number_of_significant_digits, max_digits_after_decimal, isToAlign=False):
    """
    If the value is a number (or number followed by a unit),
    this function returns a string-representation of the number
    with the specified number of significant digits,
    optionally aligned at the decimal point.
    The formatting works well only for numbers larger than 0.1.

    If the value is not a number, it is returned unchanged.
    """
    # If the number ends with "s" or another unit, remove it.
    # Units should not occur in table cells, but in the table head.
    value = remove_unit((str(s) or '').strip())
    try:
        # Round to the given amount of significant digits
        #   (unfortunately this keeps the '.0' for large numbers and removes too many zeros from the end).
        floatValue = float("{value:.{digits}g}".format(digits=number_of_significant_digits, value=float(value)))
        formattedValue = str(floatValue)
        import math
        if floatValue >= math.pow(10, number_of_significant_digits - 1):
            # There are no significant digits after the decimal point, thus remove the zeros after the point.
            formattedValue = str(round(floatValue))

        # We need to fill the missing zeros at the end because they are significant!
        # regular expression returns three groups:
        # Group 1: Digits in front of decimal point
        # Group 2: Digits after decimal point
        # Group 3: Digits after decimal point starting at the first value not 0
        m = REGEX_SIGNIFICANT_DIGITS.match(formattedValue)
        if int(m.group(1)) == 0:
            zerosToAdd = number_of_significant_digits - len(m.group(3))
        else:
            zerosToAdd = number_of_significant_digits - len(m.group(1)) - len(m.group(2))
        formattedValue += "".join(['0'] * zerosToAdd)
        # Alignment
        if isToAlign:
            formattedValue = format_number_align(formattedValue, max_digits_after_decimal)
        return formattedValue
    except ValueError: # If value is no float, don't format it.
        return s

def format_value(value, column, isToAlign=False):
    """
    Format a value nicely for human-readable output (including rounding).
    """
    if not value or value == '-':
        return '-'

    if column.type.get_type() is ColumnType.measure:

        number_of_significant_digits = column.number_of_significant_digits
        if number_of_significant_digits is None:
            number_of_significant_digits = DEFAULT_TIME_PRECISION
        max_dec_digits = column.type.max_decimal_digits

        return format_number(value, int(number_of_significant_digits), int(max_dec_digits), isToAlign)

    else:
        return value

def to_decimal(s):
    # remove whitespaces and trailing units (e.g., in '1.23s')
    s, _ = split_number_and_unit((s or '').strip())
    return Decimal(s) if s else None


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
