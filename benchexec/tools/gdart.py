# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.result as result
from benchexec.tools.template import BaseTool2


class Tool(BaseTool2):
    """
    Tool info module for GDart a tool ensemble for the dynamic symbolic execution of modern Java.
    GDart consists of three components:
    - DSE a generic dynamic symbolic execution (https://github.com/tudo-aqua/dse)
    - SPouT: Symbolic Path Recording During Testing (https://github.com/tudo-aqua/spout)
    - JConstraints: A meta solving library for SMT problems (https://github.com/tudo-aqua/jconstraints)
    """

    def executable(self, tool_locator):
        return tool_locator.find_executable("run-gdart.sh")

    def version(self, executable):
        return self._version_from_tool(executable, arg="-v")

    def name(self):
        return "GDart"

    def cmdline(self, executable, options, task, rlimits):
        cmd = [executable] + options
        if task.property_file:
            cmd.append(task.property_file)
        return cmd + list(task.input_files)

    def determine_result(self, run):
        status = result.RESULT_ERROR
        if run.output.any_line_contains("== ERROR-UNREACH-CALL"):
            status = result.RESULT_FALSE_REACH
        elif run.output.any_line_contains("== ERROR"):
            status = result.RESULT_FALSE_PROP
        elif run.output.any_line_contains("== OK"):
            status = result.RESULT_TRUE_PROP
        elif run.output.any_line_contains("== DONT-KNOW"):
            status = result.RESULT_UNKNOWN

        return status
