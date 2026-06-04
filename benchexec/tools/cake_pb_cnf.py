# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

from typing import cast

from benchexec.tools import template

from benchexec import result


class Tool(template.BaseTool2):
    """
    Tool-info module for sat solvers that were executed on the StarExec platform.
    """

    def executable(self, tool_locator):
        return tool_locator.find_executable("cake_pb_cnf")

    def version(self, executable):
        return "TODO"

    def name(self):
        return "cake_pb_cnf"

    def environment(self, executable):
        # CakeML tools layout a static heap and stack.
        # By default these are both 4GiB. We can use environment variables to
        # change it 20 GiB heap and 4 GiB stack, which fits better with the 32 GiB memory limit on apollon.
        #
        return {"newEnv": {"CML_HEAP_SIZE": "20480", "CML_STACK_SIZE": "4096"}}
        # return {}

    def cmdline(
        self, executable, options: list[str], task: template.BaseTool2.Task, rlimits
    ):
        """The proof must be the first argument in the options list."""

        return [executable, task.single_input_file, *options]

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
