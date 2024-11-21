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
    Tool info for BtorMC -- A Bounded Model Checker for Btor2
    """

    def executable(self, tool_locator):
        return tool_locator.find_executable("btormc")

    def name(self):
        return "BtorMC"

    def project_url(self):
        return "https://github.com/Boolector/boolector"

    def version(self, executable):
        return self._version_from_tool(executable)

    def cmdline(self, executable, options, task, rlimits):
        return [executable] + options + [task.single_input_file]

    def determine_result(self, run):
        """
        @return: status of BtorMC after executing a run
        """
        for line in run.output[::-1]:
            # BtorMC's option `--trace-gen` must be set to 1
            # (which is already the default setting of BtorMC)
            # such that "sat/unsat" is printed to the output
            if line.startswith("unsat"):
                return result.RESULT_TRUE_PROP
            elif line.startswith("sat"):
                return result.RESULT_FALSE_PROP
        return result.RESULT_UNKNOWN
