# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

from typing import cast

from benchexec.baseexecutor import logging
from benchexec.tools import template

from benchexec import result


class Tool(template.BaseTool2):
    """
    Tool-info module for sat solvers that were executed on the StarExec platform.
    """

    def executable(self, tool_locator):
        return tool_locator.find_executable("gratchk")

    def version(self, executable):
        return "TODO"

    def name(self):
        return "GRATchk"

    def cmdline(
        self, executable, options: list[str], task: template.BaseTool2.Task, rlimits
    ):
        mode = "sat"
        if "sat" in options:
            options.remove("sat")
        else:
            mode = "unsat"
            try:
                options.remove("unsat")
            except ValueError:
                pass

        return [executable, mode, task.single_input_file, *options]

    def determine_result(self, run: template.BaseTool2.Run):
        output = cast(template.BaseTool2.RunOutput, run.output)
        for line in output:
            line = cast(str, line)
            if line.startswith("s "):
                verdict = line.strip().split(" ")[1].strip().upper()
                try:
                    sat_arg = f"({line.strip().split(' ')[2].strip().upper()})"
                except IndexError:
                    sat_arg = ""
                if verdict == "VERIFIED":
                    return result.RESULT_TRUE_PROP + sat_arg
                elif verdict == "ERROR":
                    return result.RESULT_ERROR
        return result.RESULT_ERROR
