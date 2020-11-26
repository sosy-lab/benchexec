# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.tools.esbmc as esbmc
from benchexec.tools.template import ToolNotFoundException


class Tool(esbmc.Tool):
    """
    This class serves as tool adaptor for FuSeBMC (https://github.com/kaled-alshmrany/FuSeBMC)
    """

    REQUIRED_PATHS_TESTCOMP20 = ["esbmc", "esbmc-wrapper.py", "my_instrument"]
    REQUIRED_PATHS_TESTCOMP21 = [
        "esbmc",
        "fusebmc.py",
        "FuSeBMC_inustrment/FuSeBMC_inustrment",
        "fusebmc_output",
        "map2check-fuzzer",
    ]

    def name(self):
        return "FuSeBMC"

    def executable(self, tool_locator):
        try:
            self._version = 21
            return tool_locator.find_executable("fusebmc.py")
        except ToolNotFoundException:
            self._version = 20
            return super().executable(tool_locator)

    def program_files(self, executable):
        """
        Determine the file paths to be adopted
        """
        if self._version == 20:
            paths = self.REQUIRED_PATHS_TESTCOMP20
        elif self._version > 20:
            paths = self.REQUIRED_PATHS_TESTCOMP21
        return self._program_files_from_executable(executable, paths)
