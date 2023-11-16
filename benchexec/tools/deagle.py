# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

from benchexec.tools.sv_benchmarks_util import get_data_model_from_task, ILP32, LP64
import benchexec.result as result
import benchexec.tools.template


class Tool(benchexec.tools.template.BaseTool2):
    """
    Tool info for Deagle, an SMT-based concurrent program verification tool.
    """

    def version(self, executable):
        return self._version_from_tool(executable, arg="--version")

    def executable(self, tool_locator):
        exe = tool_locator.find_executable("deagle")
        self.ver = self.version(exe)
        return exe

    def name(self):
        return "Deagle"

    def project_url(self):
        return "https://github.com/thufv/Deagle"

    def version_geq(self, version_str1, version_str2):
        version1 = version_str1.split(".")
        version2 = version_str2.split(".")
        for i in range(len(version1)):
            if int(version1[i]) > int(version2[i]):
                return True
            if int(version1[i]) < int(version2[i]):
                return False
        return True

    def cmdline(self, executable, options, task, rlimits):
        data_model_param = get_data_model_from_task(task, {ILP32: "--32", LP64: "--64"})
        if not data_model_param:
            data_model_param = "--32"
        if self.version_geq(self.ver, "2.2"):
            return (
                [executable]
                + [task.property_file]
                + [task.single_input_file]
                + [data_model_param]
            )
        else:
            if data_model_param not in options:
                options += [data_model_param]
            return [executable] + options + [task.single_input_file]

    def determine_result(self, run):
        if run.output.any_line_contains("SUCCESSFUL"):
            status = result.RESULT_TRUE_PROP
        elif run.output.any_line_contains("FAILED"):
            status = result.RESULT_FALSE_REACH
        elif run.exit_code.value == 1:
            status = result.RESULT_UNKNOWN
        else:
            status = result.RESULT_ERROR

        return status
