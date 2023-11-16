# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.util as util
from . import cseq


class Tool(cseq.CSeqTool):
    """
    Tool info for UL-CSeq.
    """

    REQUIRED_PATHS = ["backends", "bin", "include", "ul-cseq.py"]

    def executable(self):
        return util.find_executable("ul-cseq.py")

    def name(self):
        return "UL-CSeq"
