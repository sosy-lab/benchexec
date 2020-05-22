# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.util as util
import benchexec.tools.smtlib2


class Tool(benchexec.tools.smtlib2.Smtlib2Tool):
    """
    Tool info for MathSAT.
    """

    def executable(self):
        return util.find_executable("mathsat")

    def version(self, executable):
        line = self._version_from_tool(executable, "-version")
        line = line.replace("MathSAT5 version", "")
        line = line.split("(")[0]
        return line.strip()

    def name(self):
        return "MathSAT"

    def cmdline(self, executable, options, tasks, propertyfile=None, rlimits={}):
        assert len(tasks) <= 1, "only one inputfile supported"
        return [executable] + options + tasks
