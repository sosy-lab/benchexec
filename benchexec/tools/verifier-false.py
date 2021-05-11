# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.tools.template
import benchexec.result as result


class Tool(benchexec.tools.template.BaseTool2):
    """
    Tool info for verifier false.
    It always returns the verdict FALSE.
    """

    def executable(self, tool_locator):
        return tool_locator.find_executable("verifier-false.sh")

    def name(self):
        return "verifier-false"

    def cmdline(self, executable, options, task, rlimits):
        return [executable]

    def version(self, executable):
        return self._version_from_tool(executable, arg="--version")

    def determine_result(self, run):
        return result.RESULT_FALSE_REACH
