# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.util as util
import benchexec.tools.template


class Tool(benchexec.tools.template.BaseTool):
    """
    Tool info for Legion (https://github.com/Alan32Liu/Principes).
    """

    REQUIRED_PATHS = [
        "legion-sv",
        "Legion.py",
        "__VERIFIER.c",
        "__VERIFIER32.c",
        "__VERIFIER_assume.c",
        "__VERIFIER_assume.instr.s",
        "__trace_jump.s",
        "__trace_buffered.c",
        "tracejump.py",
        "lib",
    ]

    def executable(self):
        return util.find_executable("legion-sv")

    def version(self, executable):
        return self._version_from_tool(executable)

    def name(self):
        return "Legion"
