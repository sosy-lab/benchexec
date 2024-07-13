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
    Tool info for Pono -- A Flexible and Extensible SMT-Based Model Checker
    """

    def executable(self, tool_locator):
        return tool_locator.find_executable("pono")

    def name(self):
        return "Pono"

    def project_url(self):
        return "https://github.com/stanford-centaur/pono"

    def cmdline(self, executable, options, task, rlimits):
        return [executable] + options + [task.single_input_file]

    def determine_result(self, run):
        """
        @return: status of Pono after executing a run
        """
        for line in run.output[::-1]:
            if line.startswith("unsat"):
                return result.RESULT_TRUE_PROP
            if line.startswith("sat"):
                return result.RESULT_FALSE_PROP
        return result.RESULT_ERROR
