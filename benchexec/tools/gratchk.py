# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

from benchexec.tools.sat_proof_checker_base import SatProofCheckerBase


class Tool(SatProofCheckerBase):
    """
    GRATchk is the verification component of the GRAT toolchain that checks both SAT
    and UNSAT certificates, with correctness formally proven in Isabelle/HOL.
    """

    def executable(self, tool_locator):
        return tool_locator.find_executable("gratchk")

    def name(self):
        return "GRATchk"

    def project_url(self):
        return "https://www21.in.tum.de/~lammich/grat/"

    def cmdline(self, executable, options, task, rlimits):
        options = list(options)

        # Gratchk sandwiches the input files between two options that are provided externally.
        # The order must be gratchk (sat | unsat) DIMACS_FILE GRAT_PROOF_FILE .
        # The DIMACS file is provided as the single input file of the task.
        # Both, the proof file and the mode are provided in as benchexec options,
        # so we need to extract them from the options list and construct the command line accordingly.
        mode = "sat"
        if "sat" in options:
            options.remove("sat")
        else:
            mode = "unsat"  # use unsat by default if neither is specified
            if "unsat" in options:
                options.remove("unsat")
        return [executable, mode, task.single_input_file, *options]
