# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import subprocess
import pytest
from benchexec import check_cgroups

class TestCheckCgroups:
    def execute_run_extern(self, *args, **kwargs):
        try:
            return subprocess.check_output(
                args=["python3", "-m", "benchexec.check_cgroups"] + list(args),
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                **kwargs,
            )
        except subprocess.CalledProcessError as e:
            if e.returncode != 1:  # 1 is expected if cgroups are not available
                print(e.output)
                raise e

    def test_extern_command(self, caplog):
        """Test external command."""
        with caplog.at_level("DEBUG"):
            self.execute_run_extern()

    def test_simple(self, caplog):
        """Test check_cgroups.main() with --no-thread."""
        with caplog.at_level("DEBUG"):
            try:
                check_cgroups.main(["--no-thread"])
            except SystemExit as e:
                # expected if cgroups are not available
                pytest.skip(str(e))

    def test_threaded(self, caplog):
        """Test check_cgroups.main() with threading."""
        with caplog.at_level("DEBUG"):
            try:
                check_cgroups.main([])
            except SystemExit as e:
                # expected if cgroups are not available
                pytest.skip(str(e))

    def test_thread_result_is_returned(self, caplog):
        """
        Test that an error raised by check_cgroup_availability is correctly
        re-raised in the main thread by replacing this function temporarily.
        """
        tmp = check_cgroups.check_cgroup_availability
        try:
            check_cgroups.check_cgroup_availability = lambda wait: exit(1)

            with caplog.at_level("DEBUG"), pytest.raises(SystemExit):
                check_cgroups.main([])

        finally:
            check_cgroups.check_cgroup_availability = tmp
