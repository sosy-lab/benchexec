# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2026 UniVE-SSV
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.tools.template
from benchexec import result


class Tool(benchexec.tools.template.BaseTool2):
    """
    Tool info for PyLiSA
    """

    def executable(self, tool_locator):
        return tool_locator.find_executable("pylisa")

    def version(self, executable):
        return self._version_from_tool(executable, arg="version")

    def name(self):
        return "PyLiSA"

    def project_url(self):
        return "https://github.com/lisa-analyzer/pylisa"

    def cmdline(self, executable, options, task, rlimits):
        cmd = [executable, "check"]
        if options:
            cmd += options
        if task.property_file:
            cmd += ["--property", task.property_file]
        cmd.append("--inputs")
        cmd += list(task.input_files)
        return cmd

    def determine_result(self, run):
        if run.output:
            pylisa_output = run.output[-1]
            if "TRUE" in pylisa_output:
                return result.RESULT_TRUE_PROP
            if "FALSE" in pylisa_output:
                return result.RESULT_FALSE_PROP
            if "UNKNOWN" in pylisa_output:
                return result.RESULT_UNKNOWN
        return result.RESULT_ERROR
