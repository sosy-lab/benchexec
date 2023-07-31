# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import pytest
from benchexec.util import ProcessExitCode
import tempfile
import os
import stat
import shutil

from benchexec import util

@pytest.fixture(scope="class")
def setup_test_class(request):
    request.cls.longMessage = True
    request.cls.maxDiff = None

@pytest.fixture
def temp_test_dir():
    base_dir = tempfile.mkdtemp(prefix="BenchExec_test_util_rmtree")
    yield base_dir
    # Automatically cleanup the temporary directory after the test
    shutil.rmtree(base_dir)

class TestParse:
    def test_split_number_and_unit(self):
        assert util.split_number_and_unit("1") == (1, "")
        assert util.split_number_and_unit("1s") == (1, "s")
        assert util.split_number_and_unit("  1  s  ") == (1, "s")
        assert util.split_number_and_unit("-1s") == (-1, "s")
        assert util.split_number_and_unit("1abc") == (1, "abc")
        assert util.split_number_and_unit("1  abc  ") == (1, "abc")

        with pytest.raises(ValueError):
            util.split_number_and_unit("")
        with pytest.raises(ValueError):
            util.split_number_and_unit("abc")
        with pytest.raises(ValueError):
            util.split_number_and_unit("s")
        with pytest.raises(ValueError):
            util.split_number_and_unit("a1a")

    def test_parse_memory_value(self):
        assert util.parse_memory_value("1") == 1
        assert util.parse_memory_value("1B") == 1
        assert util.parse_memory_value("1kB") == 1000
        assert util.parse_memory_value("1MB") == 1000 * 1000
        assert util.parse_memory_value("1GB") == 1000 * 1000 * 1000
        assert util.parse_memory_value("1TB") == 1000 * 1000 * 1000 * 1000

    def test_parse_timespan_value(self):
        assert util.parse_timespan_value("1") == 1
        assert util.parse_timespan_value("1s") == 1
        assert util.parse_timespan_value("1min") == 60
        assert util.parse_timespan_value("1h") == 60 * 60
        assert util.parse_timespan_value("1d") == 24 * 60 * 60

class TestProcessExitCode:
    def ProcessExitCode_with_value(self, value):
        return ProcessExitCode(raw=value << 8, value=value, signal=None)

    def ProcessExitCode_with_signal(self, signal):
        return ProcessExitCode(raw=signal, value=None, signal=signal)

    def test_boolness(self):
        assert not self.ProcessExitCode_with_value(0)
        assert self.ProcessExitCode_with_value(1)
        assert self.ProcessExitCode_with_signal(1)

    def test_value(self):
        assert self.ProcessExitCode_with_value(0).value == 0
        assert self.ProcessExitCode_with_value(1).value == 1
        assert ProcessExitCode.from_raw(0).value == 0
        assert ProcessExitCode.from_raw(256).value == 1
        assert self.ProcessExitCode_with_signal(1).value is None
        assert ProcessExitCode.from_raw(1).value is None

    def test_signal(self):
        assert self.ProcessExitCode_with_signal(1).signal == 1
        assert ProcessExitCode.from_raw(1).signal == 1
        assert self.ProcessExitCode_with_value(0).signal is None
        assert self.ProcessExitCode_with_value(1).signal is None
        assert ProcessExitCode.from_raw(0).signal is None
        assert ProcessExitCode.from_raw(256).signal is None

class TestRmtree:
    def test_writable_file(self, temp_test_dir):
        with tempfile.TemporaryDirectory(prefix="BenchExec_test_util_rmtree") as temp_test_dir:
            temp_file = os.path.join(temp_test_dir, "tempfile")
            util.write_file("", temp_file)
            assert os.path.exists(temp_file), "Failed to create temporary file"

    def test_writable_dir(self, temp_test_dir):
        with tempfile.TemporaryDirectory(prefix="BenchExec_test_util_rmtree") as temp_test_dir:
            temp_dir = os.path.join(temp_test_dir, "tempdir")
            os.mkdir(temp_dir)
            assert os.path.exists(temp_dir), "Failed to create temporary directory"

    def test_nonwritable_file(self, temp_test_dir):
        with tempfile.TemporaryDirectory(prefix="BenchExec_test_util_rmtree") as temp_test_dir:
            temp_file = os.path.join(temp_test_dir, "tempfile")
            util.write_file("", temp_file)
            os.chmod(temp_file, 0)
            assert os.path.exists(temp_file), "Failed to create temporary non-writable file"

    def create_and_delete_directory(self, mode):
        base_dir = tempfile.mkdtemp(prefix="BenchExec_test_util_rmtree")
        tempdir = os.path.join(base_dir, "tempdir")
        os.mkdir(tempdir)
        util.write_file("", tempdir, "tempfile")
        os.chmod(tempdir, mode)
        util.rmtree(base_dir)
        return base_dir

    def test_nonwritable_dir(self, temp_test_dir):
        base_dir = self.create_and_delete_directory(stat.S_IRUSR | stat.S_IXUSR)
        assert not os.path.exists(base_dir), "Failed to remove directory"

    def test_nonexecutable_dir(self, temp_test_dir):
        base_dir = self.create_and_delete_directory(stat.S_IRUSR | stat.S_IWUSR)
        assert not os.path.exists(base_dir), "Failed to remove directory"

    def test_nonreadable_dir(self, temp_test_dir):
        base_dir = self.create_and_delete_directory(stat.S_IWUSR | stat.S_IXUSR)
        assert not os.path.exists(base_dir), "Failed to remove directory"

    def test_dir_without_any_permissions(self, temp_test_dir):
        base_dir = self.create_and_delete_directory(0)
        assert not os.path.exists(base_dir), "Failed to remove directory"
