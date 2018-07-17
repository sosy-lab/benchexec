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

    def test_nan(self):
        import math
        nan = Decimal(float('nan'))
        v = Decimal(0.123)

        s = StatValue.from_list([nan])
        self.assertTrue(math.isnan(s.sum), "Not NaN, but " + str(s.sum))
        self.assertTrue(math.isnan(s.avg), "Not NaN, but " + str(s.avg))
        self.assertTrue(math.isnan(s.max), "Not NaN, but " + str(s.max))
        self.assertTrue(math.isnan(s.min), "Not NaN, but " + str(s.min))
        self.assertTrue(math.isnan(s.median), "Not NaN, but " + str(s.median))
        self.assertTrue(math.isnan(s.stdev), "Not NaN, but " + str(s.stdev))

        s = StatValue.from_list([nan, v])
        self.assertTrue(math.isnan(s.sum), "Not NaN, but " + str(s.sum))
        self.assertTrue(math.isnan(s.avg), "Not NaN, but " + str(s.avg))
        self.assertTrue(math.isnan(s.max), "Not NaN, but " + str(s.max))
        self.assertTrue(math.isnan(s.min), "Not NaN, but " + str(s.min))
        self.assertTrue(math.isnan(s.median), "Not NaN, but " + str(s.median))
        self.assertTrue(math.isnan(s.stdev), "Not NaN, but " + str(s.stdev))

    def test_one_inf(self):
        inf = Decimal(float('inf'))
        v = Decimal(0.123)

        s = StatValue.from_list([inf])
        self.assertEqual(s.sum, inf, "Not Inf, but " + str(s.sum))
        self.assertEqual(s.avg, inf, "Not Inf, but " + str(s.avg))
        self.assertEqual(s.max, inf, "Not Inf, but " + str(s.max))
        self.assertEqual(s.min, inf, "Not Inf, but " + str(s.min))
        self.assertEqual(s.median, inf, "Not Inf, but " + str(s.median))
        self.assertEqual(s.stdev, inf, "Not Inf, but " + str(s.stdev))

        s = StatValue.from_list([inf, v])
        self.assertEqual(s.sum, inf, "Not Inf, but " + str(s.sum))
        self.assertEqual(s.avg, inf, "Not NaN, but " + str(s.avg))
        self.assertEqual(s.max, inf, "Not NaN, but " + str(s.max))
        self.assertEqual(s.min, v, "Not NaN, but " + str(s.min))
        self.assertEqual(s.median, inf, "Not NaN, but " + str(s.median))
        self.assertEqual(s.stdev, inf, "Not NaN, but " + str(s.stdev))

    def test_one_negative_inf(self):
        ninf = Decimal(float('-inf'))
        inf = Decimal(float('inf'))
        v = Decimal(0.123)

        s = StatValue.from_list([ninf])
        self.assertEqual(s.sum, ninf, "Not -Inf, but " + str(s.sum))
        self.assertEqual(s.avg, ninf, "Not -Inf, but " + str(s.avg))
        self.assertEqual(s.max, ninf, "Not -Inf, but " + str(s.max))
        self.assertEqual(s.min, ninf, "Not -Inf, but " + str(s.min))
        self.assertEqual(s.median, ninf, "Not -Inf, but " + str(s.median))
        self.assertEqual(s.stdev, inf, "Not Inf, but " + str(s.stdev))

        s = StatValue.from_list([ninf, v])
        self.assertEqual(s.sum, ninf, "Not -Inf, but " + str(s.sum))
        self.assertEqual(s.avg, ninf, "Not -Inf, but " + str(s.avg))
        self.assertEqual(s.max, v, "Not 0.123, but " + str(s.max))
        self.assertEqual(s.min, ninf, "Not -Inf, but " + str(s.min))
        self.assertEqual(s.median, ninf, "Not -Inf, but " + str(s.median))
        self.assertEqual(s.stdev, inf, "Not Inf, but " + str(s.stdev))

    def test_multiple_positive_inf(self):
        inf = Decimal(float('inf'))
        v = Decimal(0.123)

        # Equal number of infs
        s = StatValue.from_list([inf, inf, v])
        self.assertEqual(s.sum, inf, "Not Inf, but " + str(s.sum))
        self.assertEqual(s.avg, inf, "Not Inf, but " + str(s.avg))
        self.assertEqual(s.max, inf, "Not Inf, but " + str(s.max))
        self.assertEqual(s.min, v, "Not 0.123, but " + str(s.min))
        self.assertEqual(s.median, inf, "Not Inf, but " + str(s.median))
        self.assertEqual(s.stdev, inf, "Not Inf, but " + str(s.stdev))

        # Unequal number of infs
        s = StatValue.from_list([inf, inf, inf, v])
        self.assertEqual(s.sum, inf, "Not Inf, but " + str(s.sum))
        self.assertEqual(s.avg, inf, "Not Inf, but " + str(s.avg))
        self.assertEqual(s.max, inf, "Not Inf, but " + str(s.max))
        self.assertEqual(s.min, v, "Not 0.123, but " + str(s.min))
        self.assertEqual(s.median, inf, "Not Inf, but " + str(s.median))
        self.assertEqual(s.stdev, inf, "Not Inf, but " + str(s.stdev))

    def test_multiple_negative_inf(self):
        ninf = Decimal(float('-inf'))
        inf = Decimal(float('inf'))
        v = Decimal(0.123)

        # Equal number of negative infs
        s = StatValue.from_list([ninf, ninf, v])
        self.assertEqual(s.sum, ninf, "Not -Inf, but " + str(s.sum))
        self.assertEqual(s.avg, ninf, "Not -Inf, but " + str(s.avg))
        self.assertEqual(s.max, v, "Not 0.123, but " + str(s.max))
        self.assertEqual(s.min, ninf, "Not -Inf, but " + str(s.min))
        self.assertEqual(s.median, ninf, "Not -Inf, but " + str(s.median))
        self.assertEqual(s.stdev, inf, "Not Inf, but " + str(s.stdev))

        # Unequal number of negative infs
        s = StatValue.from_list([ninf, ninf, ninf, v])
        self.assertEqual(s.sum, ninf, "Not -Inf, but " + str(s.sum))
        self.assertEqual(s.avg, ninf, "Not -Inf, but " + str(s.avg))
        self.assertEqual(s.max, v, "Not 0.123, but " + str(s.max))
        self.assertEqual(s.min, ninf, "Not -Inf, but " + str(s.min))
        self.assertEqual(s.median, ninf, "Not -Inf, but " + str(s.median))
        self.assertEqual(s.stdev, inf, "Not Inf, but " + str(s.stdev))

    def test_multiple_positive_and_negative_inf(self):
        import math
        inf = Decimal(float('inf'))
        ninf = Decimal(float('-inf'))
        v = Decimal(0.123)

        s = StatValue.from_list([inf, ninf, v])
        self.assertTrue(math.isnan(s.sum), "Not NaN, but " + str(s.sum))
        self.assertTrue(math.isnan(s.avg), "Not NaN, but " + str(s.avg))
        self.assertEqual(s.max, inf, "Not Inf, but " + str(s.max))
        self.assertEqual(s.min, ninf, "Not -Inf, but " + str(s.min))
        self.assertEqual(s.median, v, "Not 0.123, but " + str(s.median))
        self.assertTrue(math.isnan(s.stdev), "Not NaN, but " + str(s.stdev))
