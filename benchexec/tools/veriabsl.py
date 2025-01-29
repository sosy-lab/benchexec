# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

from . import veriabs


class Tool(veriabs.Tool):
    """
    VeriAbsL
    """

    def name(self):
        return "VeriAbsL"
