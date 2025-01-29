# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.tools.template
import benchexec.util as util


class Tool(benchexec.tools.template.BaseTool):
    """
    This tool is an trivial tool that calculates pi up to a certain number of digits using bc.
    Use this for example for testing and creating some CPU load.
    """

    def executable(self):
        return util.find_executable("bc")

    def name(self):
        return "CalculatePI"

    def cmdline(self, executable, options, tasks, propertyfile, rlimits):
        assert len(tasks) == 1
        digits = tasks[0].strip()
        assert int(digits) >= 0
        return [
            "/bin/sh",
            "-c",
            f'echo "scale={digits}; a(1)*4" | {executable} -l',
        ]
