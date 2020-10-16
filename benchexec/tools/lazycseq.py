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
    Tool info for Lazy-CSeq (http://github.com/omainv/cseq/releases).
    """

    REQUIRED_PATHS = [
        "cbmc",
        "cbmc-5.4",
        "esbmc",
        "core",
        "cseq.py",
        "lazy-cseq.py",
        "pycparser",
        "pycparserext",
        "modules",
    ]

    def executable(self):
        return util.find_executable("lazy-cseq.py")

    def name(self):
        return "Lazy-CSeq"
