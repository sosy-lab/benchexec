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
    Tool info for Mu-CSeq.
    """

    REQUIRED_PATHS = [
        "cbmc",
        "clean.py",
        "clean.pyc",
        "core",
        "cseq.py",
        "inlined.i.c",
        "lazyseq.py",
        "lextab.py",
        "merger.py",
        "merger.pyc",
        "modules",
        "mu-cseq-grained.py",
        "mu-cseq.py",
        "mu-cseq-translation.py",
        "my-include",
        "my-include-grained",
        "parametri.txt",
        "parsermu.py",
        "parsermu.pyc",
        "parser.py",
        "parser.pyc",
        "translatorgrained.py",
        "translatorgrained.pyc",
        "translator.py",
        "translator.pyc",
        "utils.py",
        "utils.pyc",
        "w-tester-check.py",
        "yacctab.py",
    ]

    def executable(self):
        return util.find_executable("mu-cseq.py")

    def name(self):
        return "Mu-CSeq"
