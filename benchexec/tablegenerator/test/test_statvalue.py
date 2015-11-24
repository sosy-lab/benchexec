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

from decimal import Decimal
import sys
import unittest
sys.dont_write_bytecode = True # prevent creation of .pyc files

from benchexec.tablegenerator import StatValue

class TestStatValue(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.longMessage = True
        cls.maxDiff = None

    def test_empty(self):
        s = StatValue.from_list([])
        self.assertEqual(s.sum, 0)
        self.assertEqual(s.avg, None)
        self.assertEqual(s.max, None)
        self.assertEqual(s.min, None)
        self.assertEqual(s.median, None)
        self.assertEqual(s.stdev, None)

    def test_single_value(self):
        v = Decimal(1.23)
        s = StatValue.from_list([v])
        self.assertAlmostEqual(s.sum, v)
        self.assertAlmostEqual(s.avg, v)
        self.assertEqual(s.max, v)
        self.assertEqual(s.min, v)
        self.assertEqual(s.median, v)
        self.assertAlmostEqual(s.stdev, Decimal(0))

    def test_two_values(self):
        v1 = Decimal(1.23)
        v2 = Decimal(4.56)
        for t in [[v1,v2], [v2,v1]]:
            s = StatValue.from_list(t)
            self.assertEqual(s.sum, v1+v2)
            self.assertAlmostEqual(s.avg, (v1+v2)/Decimal(2))
            self.assertEqual(s.max, v2)
            self.assertEqual(s.min, v1)
            self.assertAlmostEqual(s.median, (v1+v2)/Decimal(2))
            self.assertAlmostEqual(s.stdev, Decimal(1.665))

    def test_three_values(self):
        v1 = Decimal(0.123)
        v2 = Decimal(4.56)
        v3 = Decimal(789)
        for t in [[v1,v2,v3], [v3,v2,v1], [v2,v1,v3]]:
            s = StatValue.from_list(t)
            self.assertEqual(s.sum, v1+v2+v3)
            self.assertAlmostEqual(s.avg, (v1+v2+v3)/Decimal(3))
            self.assertEqual(s.max, v3)
            self.assertEqual(s.min, v1)
            self.assertEqual(s.median, v2)
            self.assertAlmostEqual(s.stdev, Decimal(370.83879721))
