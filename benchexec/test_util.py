# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

from decimal import Decimal
import unittest
from benchexec.util import ProcessExitCode
import tempfile
import os
import stat

from benchexec import util


class TestParse(unittest.TestCase):

    def assertEqualNumberAndUnit(self, value, number, unit):
        self.assertEqual(util.split_number_and_unit(value), (number, unit))

    def test_split_number_and_unit(self):
        self.assertEqualNumberAndUnit("1", 1, "")
        self.assertEqualNumberAndUnit("1s", 1, "s")
        self.assertEqualNumberAndUnit("  1  s  ", 1, "s")
        self.assertEqualNumberAndUnit("-1s", -1, "s")
        self.assertEqualNumberAndUnit("1abc", 1, "abc")
        self.assertEqualNumberAndUnit("1  abc  ", 1, "abc")

        self.assertRaises(ValueError, util.split_number_and_unit, "")
        self.assertRaises(ValueError, util.split_number_and_unit, "abc")
        self.assertRaises(ValueError, util.split_number_and_unit, "s")
        self.assertRaises(ValueError, util.split_number_and_unit, "a1a")

    def test_parse_memory_value(self):
        self.assertEqual(util.parse_memory_value("1"), 1)
        self.assertEqual(util.parse_memory_value("1B"), 1)
        self.assertEqual(util.parse_memory_value("1kB"), 1000)
        self.assertEqual(util.parse_memory_value("1MB"), 1000 * 1000)
        self.assertEqual(util.parse_memory_value("1GB"), 1000 * 1000 * 1000)
        self.assertEqual(util.parse_memory_value("1TB"), 1000 * 1000 * 1000 * 1000)

    def test_parse_timespan_value(self):
        self.assertEqual(util.parse_timespan_value("1"), 1)
        self.assertEqual(util.parse_timespan_value("1s"), 1)
        self.assertEqual(util.parse_timespan_value("1min"), 60)
        self.assertEqual(util.parse_timespan_value("1h"), 60 * 60)
        self.assertEqual(util.parse_timespan_value("1d"), 24 * 60 * 60)

    def test_print_decimal_roundtrip(self):
        # These values should be printed exactly as in the input (with "+" removed)
        test_values = [
            "NaN",
            "Inf",
            "-Inf",
            "+Inf",
            "0",
            "-0",
            "+0",
            "0.0",
            "-0.0",
            "0.00000000000000000000",
            "0.00000000000000000001",
            "0.00000000123450000000",
            "0.1",
            "0.10000000000000000000",
            "0.99999999999999999999",
            "1",
            "-1",
            "+1",
            "1000000000000000000000",
            "10000000000.0000000000",
        ]
        for value in test_values:
            expected = value.lstrip("+")
            self.assertEqual(expected, util.print_decimal(Decimal(value)))

    def test_print_decimal_int(self):
        # These values should be printed like Decimal prints them after quantizing
        # to remove the exponent.
        test_values = ["0e0", "-0e0", "0e20", "1e0", "1e20", "0e10"]
        for value in test_values:
            value = Decimal(value)
            expected = str(value.quantize(1))
            assert "e" not in expected
            self.assertEqual(expected, util.print_decimal(value))

    def test_print_decimal_float(self):
        # These values should be printed like str prints floats.
        test_values = ["1e-4", "123e-4", "1234e-4", "1234e-5", "1234e-6"]
        for value in test_values:
            expected = str(float(value))
            assert "e" not in expected, expected
            self.assertEqual(expected, util.print_decimal(Decimal(value)))


class TestProcessExitCode(unittest.TestCase):

    def ProcessExitCode_with_value(self, value):
        return ProcessExitCode(raw=value << 8, value=value, signal=None)

    def ProcessExitCode_with_signal(self, signal):
        return ProcessExitCode(raw=signal, value=None, signal=signal)

    def test_boolness(self):
        self.assertFalse(self.ProcessExitCode_with_value(0))
        self.assertTrue(self.ProcessExitCode_with_value(1))
        self.assertTrue(self.ProcessExitCode_with_signal(1))

    def test_value(self):
        self.assertEqual(self.ProcessExitCode_with_value(0).value, 0)
        self.assertEqual(self.ProcessExitCode_with_value(1).value, 1)
        self.assertEqual(ProcessExitCode.from_raw(0).value, 0)
        self.assertEqual(ProcessExitCode.from_raw(256).value, 1)
        self.assertIsNone(self.ProcessExitCode_with_signal(1).value)
        self.assertIsNone(ProcessExitCode.from_raw(1).value)

    def test_signal(self):
        self.assertEqual(self.ProcessExitCode_with_signal(1).signal, 1)
        self.assertEqual(ProcessExitCode.from_raw(1).signal, 1)
        self.assertIsNone(self.ProcessExitCode_with_value(0).signal)
        self.assertIsNone(self.ProcessExitCode_with_value(1).signal)
        self.assertIsNone(ProcessExitCode.from_raw(0).signal)
        self.assertIsNone(ProcessExitCode.from_raw(256).signal)


class TestRmtree(unittest.TestCase):
    def setUp(self):
        self.base_dir = tempfile.mkdtemp(prefix="BenchExec_test_util_rmtree")

    def test_writable_file(self):
        util.write_file("", self.base_dir, "tempfile")
        util.rmtree(self.base_dir)
        self.assertFalse(
            os.path.exists(self.base_dir), "Failed to remove directory with file"
        )

    def test_writable_dir(self):
        os.mkdir(os.path.join(self.base_dir, "tempdir"))
        util.rmtree(self.base_dir)
        self.assertFalse(
            os.path.exists(self.base_dir),
            "Failed to remove directory with child directory",
        )

    def test_nonwritable_file(self):
        temp_file = os.path.join(self.base_dir, "tempfile")
        util.write_file("", temp_file)
        os.chmod(temp_file, 0)
        util.rmtree(self.base_dir)
        self.assertFalse(
            os.path.exists(self.base_dir),
            "Failed to remove directory with non-writable file",
        )

    def create_and_delete_directory(self, mode):
        tempdir = os.path.join(self.base_dir, "tempdir")
        os.mkdir(tempdir)
        util.write_file("", tempdir, "tempfile")
        os.chmod(tempdir, mode)
        util.rmtree(self.base_dir)
        self.assertFalse(os.path.exists(self.base_dir), "Failed to remove directory")

    def test_nonwritable_dir(self):
        self.create_and_delete_directory(stat.S_IRUSR | stat.S_IXUSR)

    def test_nonexecutable_dir(self):
        self.create_and_delete_directory(stat.S_IRUSR | stat.S_IWUSR)

    def test_nonreadable_dir(self):
        self.create_and_delete_directory(stat.S_IWUSR | stat.S_IXUSR)

    def test_dir_without_any_permissions(self):
        self.create_and_delete_directory(0)
