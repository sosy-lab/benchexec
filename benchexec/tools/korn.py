# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0


import benchexec.result as result
import benchexec.tools.template

from benchexec.tools.sv_benchmarks_util import get_data_model_from_task, ILP32, LP64


class Tool(benchexec.tools.template.BaseTool2):
    """
    Tool info for Korn, a software verifier based on Horn-clauses.
    """

    REQUIRED_PATHS = [
        "run",
        "korn.jar",
        "z3",
        "golem",
        "eld",
        "eld.jar",
        "__VERIFIER.c",
        "__VERIFIER_random.c",
        "__VERIFIER_zero.c",
    ]

    def executable(self, tool_locator):
        return tool_locator.find_executable("run")

    def version(self, executable):
        return self._version_from_tool(executable)

    def name(self):
        return "Korn"

    def project_url(self):
        return "https://github.com/gernst/korn"

    def cmdline(self, executable, options, task, rlimits):
        cmd = [executable]
        cmd = cmd + options

        data_model_param = get_data_model_from_task(task, {ILP32: "-32", LP64: "-64"})

        if data_model_param and data_model_param not in options:
            cmd += [data_model_param]

        cmd = cmd + [task.single_input_file]

        return cmd

    def determine_result(self, run):
        """
        Parse structured tool output
        """

        for line in run.output:
            if "status:" in line:
                parts = line.split(":")
                if len(parts) > 1:
                    status = parts[1]
                    status = status.strip()

                    if status == "incorrect":
                        return result.RESULT_FALSE_REACH
                    elif status == "correct":
                        return result.RESULT_TRUE_PROP

            if "error:" in line:
                return result.RESULT_ERROR

        return result.RESULT_UNKNOWN

    def get_value_from_output(self, output, identifier):
        for line in reversed(output):
            if line.startswith(identifier):
                value = line[len(identifier) :]
                value = value.strip()
                return value
        return None
