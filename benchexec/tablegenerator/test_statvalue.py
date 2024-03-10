# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

from decimal import Decimal
import sys
import pytest

from benchexec.tablegenerator.statistics import StatValue

sys.dont_write_bytecode = True  # prevent creation of .pyc files


class TestStatValue:
    @classmethod
    def setup_class(cls):
        cls.long_message = True
        cls.max_diff = None

    def test_empty(self):
        assert StatValue.from_list([]) is None

    def test_single_value(self):
        v = Decimal("1.23")
        s = StatValue.from_list([v])
        assert s.sum == v
        assert s.avg == v
        assert s.max == v
        assert s.min == v
        assert s.median == v
        assert s.stdev == Decimal(0)

    def test_two_values(self):
        v1 = Decimal("1.23")
        v2 = Decimal("4.56")
        for t in [[v1, v2], [v2, v1]]:
            s = StatValue.from_list(t)
            assert s.sum == v1 + v2
            assert s.avg == (v1 + v2) / Decimal(2)
            assert s.max == v2
            assert s.min == v1
            assert s.median == (v1 + v2) / Decimal(2)
            assert s.stdev == Decimal("1.665")

    def test_three_values(self):
        v1 = Decimal("0.123")
        v2 = Decimal("4.56")
        v3 = Decimal("789")
        for t in [[v1, v2, v3], [v3, v2, v1], [v2, v1, v3]]:
            s = StatValue.from_list(t)
            assert s.sum == v1 + v2 + v3
            assert s.avg == (v1 + v2 + v3) / Decimal(3)
            assert s.max == v3
            assert s.min == v1
            assert s.median == v2
            assert pytest.approx(s.stdev, abs=1e-8) == Decimal("370.83879721")

    def test_nan(self):
        nan = Decimal("nan")
        v = Decimal("0.123")

        s = StatValue.from_list([nan])
        assert s.sum.is_nan()
        assert s.avg.is_nan()
        assert s.max.is_nan()
        assert s.min.is_nan()
        assert s.median.is_nan()
        assert s.stdev.is_nan()

        s = StatValue.from_list([nan, v])
        assert s.sum.is_nan()
        assert s.avg.is_nan()
        assert s.max.is_nan()
        assert s.min.is_nan()
        assert s.median.is_nan()
        assert s.stdev.is_nan()

    def test_one_inf(self):
        inf = Decimal("inf")
        v = Decimal("0.123")

        s = StatValue.from_list([inf])
        assert s.sum == inf
        assert s.avg == inf
        assert s.max == inf
        assert s.min == inf
        assert s.median == inf
        assert s.stdev == inf

        s = StatValue.from_list([inf, v])
        assert s.sum == inf
        assert s.avg == inf
        assert s.max == inf
        assert s.min == v
        assert s.median == inf
        assert s.stdev == inf

    def test_one_negative_inf(self):
        ninf = Decimal("-inf")
        inf = Decimal("inf")
        v = Decimal("0.123")

        s = StatValue.from_list([ninf])
        assert s.sum == ninf
        assert s.avg == ninf
        assert s.max == ninf
        assert s.min == ninf
        assert s.median == ninf
        assert s.stdev == inf

        s = StatValue.from_list([ninf, v])
        assert s.sum == ninf
        assert s.avg == ninf
        assert s.max == v
        assert s.min == ninf
        assert s.median == ninf
        assert s.stdev == inf

    def test_multiple_positive_inf(self):
        inf = Decimal("inf")
        v = Decimal("0.123")

        s = StatValue.from_list([inf, inf, v])
        assert s.sum == inf
        assert s.avg == inf
        assert s.max == inf
        assert s.min == v
        assert s.median == inf
        assert s.stdev == inf

        s = StatValue.from_list([inf, inf, inf, v])
        assert s.sum == inf
        assert s.avg == inf
        assert s.max == inf
        assert s.min == v
        assert s.median == inf
        assert s.stdev == inf

    def test_multiple_negative_inf(self):
        ninf = Decimal("-inf")
        inf = Decimal("inf")
        v = Decimal("0.123")

        s = StatValue.from_list([ninf, ninf, v])
        assert s.sum == ninf
        assert s.avg == ninf
        assert s.max == v
        assert s.min == ninf
        assert s.median == ninf
        assert s.stdev == inf

        s = StatValue.from_list([ninf, ninf, ninf, v])
        assert s.sum == ninf
        assert s.avg == ninf
        assert s.max == v
        assert s.min == ninf
        assert s.median == ninf
        assert s.stdev == inf

    def test_multiple_positive_and_negative_inf(self):
        inf = Decimal("inf")
        ninf = Decimal("-inf")
        v = Decimal("0.123")

        s = StatValue.from_list([inf, ninf, v])
        assert s.sum.is_nan()
        assert s.avg.is_nan()
        assert s.max == inf
        assert s.min == ninf
        assert s.median == v
        assert s.stdev.is_nan()
