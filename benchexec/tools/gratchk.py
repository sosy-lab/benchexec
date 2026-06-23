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

        # GRATchk requires a mode as its first argument: gratchk (sat|unsat) DIMACS PROOF
        # The mode must be the first benchexec option; remaining options are the proof file(s).
        return [executable, options[0], task.single_input_file, *options[1:]]
