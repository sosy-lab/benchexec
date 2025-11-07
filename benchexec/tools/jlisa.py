# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2025 UniVE-SSV
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.tools.template
import benchexec.result as result


class Tool(benchexec.tools.template.BaseTool2):
    """
    Tool info for JLiSA
    """

    def executable(self, tool_locator):
        return tool_locator.find_executable("jlisa")

    def version(self, executable):
        return self._version_from_tool(executable, arg="version")

    def name(self):
        return "JLiSA"

    def project_url(self):
        return "https://github.com/lisa-analyzer/jlisa"

    def cmdline(self, executable, options, task, rlimits):
        cmd = [executable, "check", "--inputs", " ".join(task.input_files)]
        if task.property_file:
            cmd += ["--property", task.property_file]
        return cmd

    def determine_result(self, run):
        if len(run.output) > 0:
            jlisa_output = run.output[-1]
            if "TRUE" in jlisa_output:
                return result.RESULT_TRUE_PROP
            if "FALSE" in jlisa_output:
                return result.RESULT_FALSE_PROP
            if "UNKNOWN" in jlisa_output:
                return result.RESULT_UNKNOWN
        return result.RESULT_UNKNOWN
