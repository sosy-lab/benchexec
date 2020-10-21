# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.tools.esbmc as esbmc


class Tool(esbmc.Tool):
    """
    This class serves as tool adaptor for FuSeBMC (https://github.com/kaled-alshmrany/FuSeBMC)
    """

    REQUIRED_PATHS = ["esbmc", "esbmc-wrapper.py", "my_instrument"]

    def name(self):
        return "FuSeBMC"
