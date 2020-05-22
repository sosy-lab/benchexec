# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.tools.cpachecker as cpachecker
import benchexec.util as util


class Tool(cpachecker.Tool):
    """
    Tool info for CPA-witness2test.
    """

    def executable(self):
        # Makes sure that CPAchecker can be called, shows a warning otherwise
        super(Tool, self).executable()
        return util.find_executable(
            "cpa_witness2test.py", "scripts/cpa_witness2test.py"
        )

    def version(self, executable):
        stdout = self._version_from_tool(executable, "-version")
        version = stdout.split("(")[0].strip()
        return version

    def name(self):
        return "CPA-witness2test"

    def cmdline(self, executable, options, tasks, propertyfile=None, rlimits={}):
        additional_options = self._get_additional_options(
            options, propertyfile, rlimits
        )
        # Add additional options in front of existing ones, since -gcc-args ... must be last argument in front of task
        return [executable] + additional_options + options + tasks
