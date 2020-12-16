#!/usr/bin/env python3

# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import logging
import os
import sys

sys.dont_write_bytecode = True  # prevent creation of .pyc files
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from vcloud.vcloudbenchmarkbase import VcloudBenchmarkBase  # noqa E402
from benchexec import __version__  # noqa E402
import benchexec.benchexec  # noqa E402
import benchexec.tools  # noqa E402


class VcloudBenchmark(VcloudBenchmarkBase):
    """
    Benchmark class that defines the load_executor function.
    """

    def load_executor(self):
        import vcloud.benchmarkclient_executor as executor

        logging.debug(
            "This is vcloud-benchmark.py (based on benchexec %s) "
            "using the VerifierCloud internal API.",
            __version__,
        )

        return executor


if __name__ == "__main__":
    benchexec.benchexec.main(VcloudBenchmark())
