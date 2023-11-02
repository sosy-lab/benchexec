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
    Tool info for RELAY adapted for BenchExec.
    URL: https://github.com/vesalvojdani/relay-sv
    """

    def executable(self, tool_locator):
        return tool_locator.find_executable("run_relay.sh")

    def version(self, executable):
        return self._version_from_tool(executable, line_prefix="Version: ")

    def name(self):
        return "relay-sv"

    def cmdline(self, executable, options, task, rlimits):
        return [executable, *options, *task.input_files]

    def determine_result(self, run):
        status = result.RESULT_ERROR
        if run.output:
            if run.output.any_line_contains("Possible race"):
                status = result.RESULT_UNKNOWN
            elif run.output.any_line_contains("Fatal error"):
                status = result.RESULT_ERROR
            else:
                status = result.RESULT_TRUE_PROP
        return status
