# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.result as result
import benchexec.tools.template
from benchexec.tools.template import ToolNotFoundException


class Tool(benchexec.tools.template.BaseTool2):
    """
    Tool info for gazer-theta
    (combined tool of Gazer and Theta)
    https://github.com/ftsrg/gazer
    https://github.com/ftsrg/theta
    """

    REQUIRED_PATHS = ["."]

    def executable(self, tool_locator):
        try:
            return tool_locator.find_executable("gazer-start.sh")
        except ToolNotFoundException:
            self.REQUIRED_PATHS = [".."]
            return tool_locator.find_executable("gazer_starter.py", subdir="scripts")

    def name(self):
        return "gazer-theta"

    def version(self, executable):
        return self._version_from_tool(executable)

    def cmdline(self, executable, options, task, rlimits):
        # possible option: --output (default value if flag isn't used: working directory)
        return [executable] + options + [task.single_input_file]

    def determine_result(self, run):
        status = result.RESULT_UNKNOWN
        for line in run.output:
            if "Result of gazer-theta run: FALSE" in line:
                status = result.RESULT_FALSE_REACH
            elif "Result of gazer-theta run: TRUE" in line:
                status = result.RESULT_TRUE_PROP

        if (
            not run.was_timeout
            and status == result.RESULT_UNKNOWN
            and run.exit_code.value != 0
        ):
            status = result.RESULT_ERROR

        return status
