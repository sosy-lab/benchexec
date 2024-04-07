# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

from benchexec.tools.template import BaseTool2


class Tool(BaseTool2):
    """
    Tool info for Coccinelle.
    Coccinelle is a tool that takes a c task and a .cocci template, it injects
    faults into the given task and returns the generated mutant.
    The provided template dictates if a fault is to be injected into the program, and at which position in the code.
    """

    REQUIRED_PATHS = ["standard.h" "ocaml" "standard.iso"]

    def name(self):
        return "Coccinelle"

    def executable(self, tool_locator):
        return tool_locator.find_executable("spatch")

    def version(self, executable):
        return self._version_from_tool(
            executable, arg="--version", line_prefix="spatch version"
        )

    def cmdline(self, executable, options, task, resource_limits):
        return [executable] + options + [task.single_input_file]

    def project_url(self):
        return "https://github.com/coccinelle/coccinelle"
