# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.result as result
import benchexec.tools.template


class Tool(benchexec.tools.template.BaseTool2):
    """
    Tool info for Kissat SAT Solver.
    """

    def executable(self, tool_locator):
        return tool_locator.find_executable("kissat", subdir="build")

    def name(self):
        return "Kissat"

    def project_url(self):
        return "http://fmv.jku.at/kissat/"

    def version(self, executable):
        return self._version_from_tool(executable)

    def cmdline(self, executable, options, task, rlimits):
        return [executable] + options + [task.single_input_file]

    def determine_result(self, run):
        """
        @return: status of Kissat after executing a run
        """

        status = None

        for line in run.output:
            if "s SATISFIABLE" in line:
                status = result.RESULT_TRUE_PROP
            elif "s UNSATISFIABLE" in line:
                status = result.RESULT_FALSE_PROP

        if not status:
            status = result.RESULT_ERROR
        return status
