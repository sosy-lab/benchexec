# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

from decimal import Decimal
import sys
import unittest

from benchexec.tablegenerator.statistics import StatValue

sys.dont_write_bytecode = True  # prevent creation of .pyc files


class TestStatValue(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.longMessage = True
        cls.maxDiff = None

    def test_empty(self):
        self.assertIsNone(StatValue.from_list([]))

    def test_single_value(self):
        v = Decimal("1.23")
        s = StatValue.from_list([v])
        self.assertEqual(s.sum, v)
        self.assertEqual(s.avg, v)
        self.assertEqual(s.max, v)
        self.assertEqual(s.min, v)
        self.assertEqual(s.median, v)
        self.assertEqual(s.stdev, Decimal(0))

    def test_two_values(self):
        v1 = Decimal("1.23")
        v2 = Decimal("4.56")
        for t in [[v1, v2], [v2, v1]]:
            s = StatValue.from_list(t)
            self.assertEqual(s.sum, v1 + v2)
            self.assertEqual(s.avg, (v1 + v2) / Decimal(2))
            self.assertEqual(s.max, v2)
            self.assertEqual(s.min, v1)
            self.assertEqual(s.median, (v1 + v2) / Decimal(2))
            self.assertEqual(s.stdev, Decimal("1.665"))

    def test_three_values(self):
        v1 = Decimal("0.123")
        v2 = Decimal("4.56")
        v3 = Decimal("789")
        for t in [[v1, v2, v3], [v3, v2, v1], [v2, v1, v3]]:
            s = StatValue.from_list(t)
            self.assertEqual(s.sum, v1 + v2 + v3)
            self.assertEqual(s.avg, (v1 + v2 + v3) / Decimal(3))
            self.assertEqual(s.max, v3)
            self.assertEqual(s.min, v1)
            self.assertEqual(s.median, v2)
            self.assertAlmostEqual(s.stdev, Decimal("370.83879721"))

    def test_nan(self):
        nan = Decimal("nan")
        v = Decimal("0.123")

        s = StatValue.from_list([nan])
        self.assertTrue(s.sum.is_nan(), "Not NaN, but " + str(s.sum))
        self.assertTrue(s.avg.is_nan(), "Not NaN, but " + str(s.avg))
        self.assertTrue(s.max.is_nan(), "Not NaN, but " + str(s.max))
        self.assertTrue(s.min.is_nan(), "Not NaN, but " + str(s.min))
        self.assertTrue(s.median.is_nan(), "Not NaN, but " + str(s.median))
        self.assertTrue(s.stdev.is_nan(), "Not NaN, but " + str(s.stdev))

        s = StatValue.from_list([nan, v])
        self.assertTrue(s.sum.is_nan(), "Not NaN, but " + str(s.sum))
        self.assertTrue(s.avg.is_nan(), "Not NaN, but " + str(s.avg))
        self.assertTrue(s.max.is_nan(), "Not NaN, but " + str(s.max))
        self.assertTrue(s.min.is_nan(), "Not NaN, but " + str(s.min))
        self.assertTrue(s.median.is_nan(), "Not NaN, but " + str(s.median))
        self.assertTrue(s.stdev.is_nan(), "Not NaN, but " + str(s.stdev))

    def test_one_inf(self):
        inf = Decimal("inf")
        v = Decimal("0.123")

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
        ninf = Decimal("-inf")
        inf = Decimal("inf")
        v = Decimal("0.123")

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
        inf = Decimal("inf")
        v = Decimal("0.123")

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
        ninf = Decimal("-inf")
        inf = Decimal("inf")
        v = Decimal("0.123")

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
        inf = Decimal("inf")
        ninf = Decimal("-inf")
        v = Decimal("0.123")

        s = StatValue.from_list([inf, ninf, v])
        self.assertTrue(s.sum.is_nan(), "Not NaN, but " + str(s.sum))
        self.assertTrue(s.avg.is_nan(), "Not NaN, but " + str(s.avg))
        self.assertEqual(s.max, inf, "Not Inf, but " + str(s.max))
        self.assertEqual(s.min, ninf, "Not -Inf, but " + str(s.min))
        self.assertEqual(s.median, v, "Not 0.123, but " + str(s.median))
        self.assertTrue(s.stdev.is_nan(), "Not NaN, but " + str(s.stdev))
