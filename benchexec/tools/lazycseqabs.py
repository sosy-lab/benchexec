# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

from . import cseq


class Tool(cseq.CSeqTool):
    """
    Tool info for Lazy CSeq + Abstract Interpretation.
    """

    def executable(self, tool_locator):
        return tool_locator.find_executable("lazy-cseq-abs.py")

    def name(self):
        return "Lazy-CSeq-Abs"
