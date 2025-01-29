# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import subprocess

import benchexec.util as util
import benchexec.tools.smtlib2


class Tool(benchexec.tools.smtlib2.Smtlib2Tool):
    """
    Tool info for SMTInterpol.
    """

    def executable(self):
        return util.find_executable("java")

    def version(self, executable):
        stderr = subprocess.run(
            self.cmdline(executable, ["-version"], []),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        ).stderr
        line = next(
            line for line in stderr.splitlines() if line.startswith("SMTInterpol")
        )
        line = line.replace("SMTInterpol", "")
        return line.strip()

    def name(self):
        return "SMTInterpol"

    def cmdline(self, executable, options, tasks, propertyfile=None, rlimits={}):
        assert len(tasks) <= 1, "only one inputfile supported"
        return [executable, "-jar", "smtinterpol.jar"] + options + tasks
