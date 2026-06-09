# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

from benchexec.tools.sat_proof_checker_base import SatProofCheckerBase


class Tool(SatProofCheckerBase):
    """
    Cake LPR is a formally verified checker for LRAT and LPR unsatisfiability proofs,
    with correctness proven down to the compiled machine code using the CakeML compiler
    and the HOL4 theorem prover.
    """

    def executable(self, tool_locator):
        return tool_locator.find_executable("cake_lpr")

    def name(self):
        return "Cake LPR"

    def project_url(self):
        return "https://github.com/tanyongkiam/cake_lpr"
