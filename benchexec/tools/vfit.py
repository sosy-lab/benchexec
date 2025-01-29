# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

from benchexec.tools.template import BaseTool2


class Tool(BaseTool2):
    """
    Tool info for VFIT.
    V-FIT (Verified Fault Injection Tool) is a tool that is designed to generate/reproduce a benchmark set of verified
    fault-injected tasks.
    It incorporates Coveriteam for verification with CPAchecker and UAutomizer.
    """

    REQUIRED_PATHS = []

    def name(self):
        return "V-Fit"

    def executable(self, tool_locator):
        return tool_locator.find_executable("vfit")

    def version(self, executable):
        return self._version_from_tool(
            executable, arg="--version", line_prefix="v-fit version"
        )

    def cmdline(self, executable, options, task, resource_limits):
        return [executable] + options + ["--c"] + [task.single_input_file]

    def project_url(self):
        return "https://gitlab.com/sosy-lab/software/fault-injection"
