# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

from benchexec.tools.sat_proof_checker_base import SatProofCheckerBase


class Tool(SatProofCheckerBase):
    """
    DPR-Trim checks and trims proofs in the Propagation Redundancy (PR) format and
    converts them to LPR format for checking by verified proof checkers.
    """

    def executable(self, tool_locator):
        return tool_locator.find_executable("dpr-trim")

    def name(self):
        return "DPR-Trim"

    def project_url(self):
        return "https://github.com/marijnheule/dpr-trim"
