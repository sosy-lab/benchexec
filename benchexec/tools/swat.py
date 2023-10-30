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
    Tool info module for SWAT a tool ensemble for the dynamic symbolic execution of modern Java.
    """

    def executable(self, tool_locator):
        return tool_locator.find_executable("run-swat.sh")

    def version(self, executable):
        return '42'

    def name(self):
        return "SWAT"

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
