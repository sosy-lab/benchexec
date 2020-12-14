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

from vcloud.benchmarkbase import BenchmarkBase # noqa E402
from benchexec import __version__ # noqa E402
import benchexec.benchexec # noqa E402
import benchexec.tools # noqa E402

# Add ./benchmark/tools to __path__ of benchexec.tools package
# such that additional tool-wrapper modules can be placed in this directory.
benchexec.tools.__path__ = [
    os.path.join(os.path.dirname(__file__), "benchmark", "tools")
] + benchexec.tools.__path__


class Benchmark(BenchmarkBase):
    """
    Benchmark class that defines the load_executor function.
    """

    def load_executor(self):
        if self.config.cloud:
            import vcloud.benchmarkclient_executor as executor
            logging.debug(
                "This is vcloud-benchmark.py (based on benchexec %s) "
                "using the VerifierCloud internal API.",
                __version__,
            )
        else:
            executor = super(Benchmark, self).load_executor()

        return executor


if __name__ == "__main__":
    benchexec.benchexec.main(Benchmark())
