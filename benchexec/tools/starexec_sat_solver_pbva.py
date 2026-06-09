# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.tools.starexec_sat_solver


class Tool(benchexec.tools.starexec_sat_solver.Tool):
    """
    Generic tool-info for SAT Competition solvers distributed as StarExec
    archives with a starexec_run_pbva launcher script in a "bin/" subdirectory.
    """

    def executable(self, tool_locator):
        return tool_locator.find_executable("starexec_run_pbva", subdir="bin")
