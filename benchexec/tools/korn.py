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
    Tool info for Korn, a software verifier based on Horn-clauses.
    """

    REQUIRED_PATHS = [
        "run",
        "korn.jar",
        "z3",
        "eld",
        "eld.jar",
        "__VERIFIER.c",
        "__VERIFIER_random.c",
    ]

    def executable(self, tool_locator):
        return tool_locator.find_executable("run")

    def version(self, executable):
        return self._version_from_tool(executable)

    def name(self):
        return "Korn"

    def project_url(self):
        return "https://github.com/gernst/korn"

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
