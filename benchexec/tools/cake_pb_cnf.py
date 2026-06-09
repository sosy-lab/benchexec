# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

from benchexec.tools.sat_proof_checker_base import SatProofCheckerBase


class Tool(SatProofCheckerBase):
    """
    CakePB is a formally verified checker for pseudo-Boolean unsatisfiability proofs,
    providing machine-checked correctness guarantees for the VeriPB proof format.
    """

    def executable(self, tool_locator):
        return tool_locator.find_executable("cake_pb_cnf")

    def name(self):
        return "CakePB"

    def project_url(self):
        return "https://gitlab.com/MIAOresearch/software/cakepb"
