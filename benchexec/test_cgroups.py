# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import subprocess
import sys
import unittest
from unittest.mock import patch

import pytest

from benchexec import check_cgroups


class TestCheckCgroups(unittest.TestCase):
    def execute_run_extern(self, *args, **kwargs):
        try:
            return subprocess.check_output(
                args=["python3", "-m", "benchexec.check_cgroups"] + list(args),
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                **kwargs,
            )
        except subprocess.CalledProcessError as e:
            if e.returncode == 1:
                pytest.xfail("cgroups not availalle")
            raise e

    def test_extern_command(self):
        self.execute_run_extern()

    @pytest.mark.xfail(raises=SystemExit, reason="cgroups not available")
    def test_simple(self):
        check_cgroups.main(["--no-thread"])

    @pytest.mark.xfail(raises=SystemExit, reason="cgroups not available")
    def test_threaded(self):
        check_cgroups.main([])

    @patch(
        "benchexec.check_cgroups.check_cgroup_availability",
        new=lambda wait: sys.exit(1),
    )
    def test_thread_result_is_returned(self):
        """
        Test that an error raised by check_cgroup_availability is correctly
        re-raised in the main thread by replacing this function temporarily.
        """
        with self.assertRaises(SystemExit):
            check_cgroups.main([])
