# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

from benchexec.tools.sat_proof_checker_base import SatProofCheckerBase


class Tool(SatProofCheckerBase):
    """
    GRAT-Gen converts standard DRAT unsatisfiability proofs into the GRAT format,
    enabling efficient verification by the formally verified GRATchk checker.
    """

    def executable(self, tool_locator):
        return tool_locator.find_executable("gratgen")

    def name(self):
        return "GRAT-Gen"

    def project_url(self):
        return "https://www21.in.tum.de/~lammich/grat/"
