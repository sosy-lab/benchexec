# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import logging
import subprocess
import pytest

from benchexec import check_cgroups

@pytest.fixture(scope='function')
def enable_logging(request):
    """Fixture to enable logging for a specific test function."""
    logging.basicConfig(level=logging.DEBUG)

    def disable_logging():
        logging.disable(logging.CRITICAL)

    request.addfinalizer(disable_logging)

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

    def test_extern_command(self, enable_logging):
        """Test external command."""
        self.execute_run_extern()

    def test_simple(self, enable_logging):
        """Test check_cgroups.main() with --no-thread."""
        try:
            check_cgroups.main(["--no-thread"])
        except SystemExit as e:
            # expected if cgroups are not available
            pytest.skip(str(e))

    def test_threaded(self, enable_logging):
        """Test check_cgroups.main() with threading."""
        try:
            check_cgroups.main([])
        except SystemExit as e:
            # expected if cgroups are not available
            pytest.skip(str(e))

    def test_thread_result_is_returned(self, enable_logging):
        """
        Test that an error raised by check_cgroup_availability is correctly
        re-raised in the main thread by replacing this function temporarily.
        """
        tmp = check_cgroups.check_cgroup_availability
        try:
            check_cgroups.check_cgroup_availability = lambda wait: exit(1)

            with pytest.raises(SystemExit):
                check_cgroups.main([])

        finally:
            check_cgroups.check_cgroup_availability = tmp
