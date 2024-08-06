#!/usr/bin/env python3

# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
# SPDX-FileCopyrightText: 2024 Levente Bajczi
# SPDX-FileCopyrightText: Critical Systems Research Group
# SPDX-FileCopyrightText: Budapest University of Technology and Economics <https://www.ftsrg.mit.bme.hu>
#
# SPDX-License-Identifier: Apache-2.0

import logging
import os
import sys

import benchexec.benchexec
import benchexec.tools
import benchexec.util

sys.dont_write_bytecode = True  # prevent creation of .pyc files

# Add ./benchmark/tools to __path__ of benchexec.tools package
# such that additional tool-wrapper modules can be placed in this directory.
benchexec.tools.__path__ = [
    os.path.join(os.path.dirname(__file__), "benchmark", "tools")
] + benchexec.tools.__path__


class Benchmark(benchexec.benchexec.BenchExec):
    """
    An extension of BenchExec to execute benchmarks using SLURM,
    optionally via Singularity.
    """

    def create_argument_parser(self):
        parser = super(Benchmark, self).create_argument_parser()

        slurm_args = parser.add_argument_group("Options for using SLURM")
        slurm_args.add_argument(
            "--slurm",
            dest="slurm",
            action="store_true",
            help="Use SLURM to execute benchmarks.",
        )
        slurm_args.add_argument(
            "--singularity",
            dest="singularity",
            type=str,
            help="The path to the singularity .sif file to use. Will bind $PWD to $HOME when run.",
        )
        slurm_args.add_argument(
            "--scratchdir",
            dest="scratchdir",
            type=str,
            default="./",
            help="The directory where temporary directories can be created for use within singularity.",
        )
        slurm_args.add_argument(
            "--retry-killed",
            dest="retry",
            type=int,
            default="0",
            help="Retry killed jobs this many times. Use -1 for unbounded retry attempts.",
        )

        return parser

    def load_executor(self):
        if self.config.slurm:
            from slurm import slurmexecutor as executor
        else:
            logging.warning(
                "SLURM flag was not specified. Benchexec will be executed only on the local machine."
            )
            executor = super(Benchmark, self).load_executor()

        return executor


if __name__ == "__main__":
    benchexec.benchexec.main(Benchmark())
