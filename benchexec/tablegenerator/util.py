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

import tempita

DEFAULT_TIME_PRECISION = 3


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

def format_number(s, number_of_significant_digits, isToAlign=False):
    """
    If the value is a number (or number plus one char),
    this function returns a string-representation of the number
    with the specified number of significant digits.

    If the value is no number, it is returned unchanged.
    """
    # If the number ends with "s" or another unit, remove it.
    # Units should not occur in table cells, but in the table head.
    value = remove_unit((str(s) or '').strip())
    try:
        # Round to the given amount of significant digits
        #   (unfortunately this keeps the '.0' for large numbers and removes too many zeros from the end).
        floatValue = float("{value:.{digits}g}".format(digits=number_of_significant_digits, value=float(value)))
        import math
        if floatValue >= math.pow(10, number_of_significant_digits - 1):
            # There are no significant digits after the decimal point, thus remove the zeros after the point.
            formattedValue = str(round(floatValue))
        else:
            formattedValue = str(floatValue)
        # There is a decimal point involved, thus we need to fill the missing zeros at the end.
        zerosToAdd = 0
        if formattedValue.startswith('0.') and len(formattedValue) < number_of_significant_digits + 2:
            zerosToAdd = number_of_significant_digits + 2 - len(formattedValue)
        elif formattedValue.find('.') >= 0 and len(formattedValue) < number_of_significant_digits + 1:
            zerosToAdd = number_of_significant_digits + 1 - len(formattedValue)
        formattedValue += "".join(['0'] * zerosToAdd)
        # Alignment
        if isToAlign:
            alignment = number_of_significant_digits + 1
            if formattedValue.find('.') >= 0:
              alignment -= len(formattedValue) - 1
            formattedValue += "".join(['&#160;'] * alignment)
        return formattedValue
    except ValueError: # If value is no float, don't format it.
        return s

def format_value(value, column, isToAlign=False):
    """
    Format a value nicely for human-readable output (including rounding).
    """
    if not value or value == '-':
        return '-'

    number_of_significant_digits = column.number_of_significant_digits
    if number_of_significant_digits is None and column.title.lower().endswith('time'):
        number_of_significant_digits = DEFAULT_TIME_PRECISION

    if number_of_significant_digits is None:
        return value
    return format_number(value, int(number_of_significant_digits), isToAlign)

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
