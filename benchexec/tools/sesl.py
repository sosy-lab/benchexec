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
    A Symbolic Executor based on Separation Logic
    https://spencerl-y.github.io/SESL/
    """

    REQUIRED_PATHS = [
        "bin",
        "libs",
        "scripts",
        "libs/slah/lib",
        "libs/z3/lib",
        "sesl-svcomp.sh",
    ]

    def executable(self, tool_locator):
        return tool_locator.find_executable("sesl-svcomp.sh")

    def name(self):
        return "SESL"

    def version(self, executable):
        return self._version_from_tool(executable, arg="--version")

    def cmdline(self, executable, options, task, rlimits):
        options += ["-t", "--sh-mem-leak", "--add-line-info"]
        if task.property_file:
            options += ["--svcomp-property", task.property_file]
        options += [task.single_input_file]
        return [executable] + options

    def determine_result(self, run):
        if run.output.any_line_contains("INVALID_DEREF"):
            return result.RESULT_FALSE_DEREF
        elif run.output.any_line_contains("INVALID_FREE"):
            return result.RESULT_FALSE_FREE
        elif run.output.any_line_contains("Memtrack"):
            return result.RESULT_FALSE_MEMTRACK
        elif run.output.any_line_contains("Memcleanup"):
            return result.RESULT_FALSE_MEMCLEANUP
        elif run.output.any_line_contains("CHECKUNKNOWN"):
            return result.RESULT_UNKNOWN
        return result.RESULT_ERROR
