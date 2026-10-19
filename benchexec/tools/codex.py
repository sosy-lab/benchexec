# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2023 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.tools.template
from benchexec import result


class Tool(benchexec.tools.template.BaseTool2):
    """Tool info for Codex."""

    def executable(self, tool_locator):
        return tool_locator.find_executable("codex-svcomp")

    def version(self, executable):
        return self._version_from_tool(executable, "--version")

    def name(self):
        return "Codex"

    def cmdline(self, executable, options, task, rlimits):
        return [
            executable,
            task.single_input_file,
            task.property_file,
            *options,
        ]

    def determine_result(self, run):
        if run.was_timeout or run.exit_code.value == 124:
            return result.RESULT_TIMEOUT

        if run.exit_code.value != 0:
            return result.RESULT_ERROR

        for line in run.output:
            if "TRUE" in line:
                return result.RESULT_TRUE_PROP
            elif "FALSE" in line:
                return result.RESULT_FALSE_PROP
            elif "UNKNOWN" in line:
                return result.RESULT_UNKNOWN

        return result.RESULT_ERROR
