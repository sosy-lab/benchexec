# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

from benchexec.tools.symbiotic import Tool as SymbioticTool


class Tool(SymbioticTool):
    """
    Re3ver tool info object
    """

    def name(self):
        """
        Return the name of the tool, formatted for humans.
        """
        return "Re3ver"

    def project_url(self):
        return "https://gitlab.fi.muni.cz/xstepkov/reverser"

    def _getPhase(self, output):
        lastphase = "before-instr"
        for line in output:
            if line.startswith("INFO: Starting reverser"):
                lastphase = "reversing"
            elif line.startswith("INFO: Reverser time"):
                lastphase = "reversing-finished"
            if line.startswith("INFO: Starting instrumentation"):
                lastphase = "instrumentation"
            elif line.startswith("INFO: Instrumentation time"):
                lastphase = "instr-finished"
            elif line.startswith("INFO: Starting slicing"):
                lastphase = "slicing"
            elif line.startswith("INFO: Total slicing time"):
                lastphase = "slicing-finished"
            elif line.startswith("INFO: Starting verification"):
                lastphase = "verification"
            elif line.startswith("INFO: Verification time"):
                lastphase = "verification-finished"
            elif line.startswith("INFO: Replaying error path"):
                lastphase = "cex-confirmation"
            elif line.startswith("INFO: Replaying error path time"):
                lastphase = "cex-confirmation-finished"

        return lastphase
