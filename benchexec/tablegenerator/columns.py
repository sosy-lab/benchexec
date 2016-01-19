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

__all__ = ['Column, ColumnType, ColumnMeasureType']

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
        self.number_of_significant_digits = num_of_digits
        self.type = col_type
        self.unit = unit
        self.scale_factor = float(scale_factor) if scale_factor else 1
        if int(self.scale_factor) == self.scale_factor:
            self.scale_factor = int(self.scale_factor)
        self.href = href

