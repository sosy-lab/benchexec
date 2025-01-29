# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
# SPDX-FileCopyrightText: 2021 Marek Chalupa
#
# SPDX-License-Identifier: Apache-2.0

from benchexec.tools.symbiotic import Tool as SymbioticTool


class Tool(SymbioticTool):
    """
    Symbiotic-Witch tool info object
    """

    def name(self):
        """
        Return the name of the tool, formatted for humans.
        """
        return "symbiotic-witch"

    def project_url(self):
        return "https://github.com/staticafi/symbiotic"
