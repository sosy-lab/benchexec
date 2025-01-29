# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

from benchexec.tools.sv_benchmarks_util import get_data_model_from_task, ILP32, LP64
import benchexec.tools.template
import benchexec.result as result


class Tool(benchexec.tools.template.BaseTool2):
    """
    Tool info for BRICK
    """

    def executable(self, tool_locator):
        return tool_locator.find_executable("brick", subdir="bin")

    def name(self):
        return "BRICK"

    def project_url(self):
        return "https://github.com/brick-tool-dev/BRICK-2.0"

    def cmdline(self, executable, options, task, rlimits):
        data_model_param = get_data_model_from_task(task, {ILP32: "--32", LP64: "--64"})
        if data_model_param and data_model_param not in options:
            options += [data_model_param]

        return [executable] + options + list(task.input_files_or_identifier)

    def version(self, executable):
        return self._version_from_tool(executable, arg="--version")

    def program_files(self, executable):
        paths = self.REQUIRED_PATHS
        return [executable] + self._program_files_from_executable(
            executable, paths, parent_dir=True
        )

    def determine_result(self, run):
        status = result.RESULT_ERROR

        for line in run.output:
            if line == "VERIFICATION SUCCESSFUL":
                status = result.RESULT_TRUE_PROP
                break
            elif line == "VERIFICATION FAILED":
                status = result.RESULT_FALSE_REACH
                break
            elif line == "VERIFICATION UNKNOWN" or line == "VERIFICATION BOUNDED TRUE":
                status = result.RESULT_UNKNOWN
                break

        return status
