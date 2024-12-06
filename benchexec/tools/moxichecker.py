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
    Tool info for MoXIchecker
    """

    REQUIRED_PATHS = ["moxichecker/", "lib/"]

    def executable(self, tool_locator):
        return tool_locator.find_executable("moxichecker", subdir="bin")

    def name(self):
        return "MoXIchecker"

    def project_url(self):
        return "https://gitlab.com/sosy-lab/software/moxichecker"

    def version(self, executable):
        return self._version_from_tool(executable)

    def program_files(self, executable):
        return [executable] + self._program_files_from_executable(
            executable, self.REQUIRED_PATHS, parent_dir=True
        )

    def cmdline(self, executable, options, task, rlimits):
        return [executable, *options, task.single_input_file]

    def determine_result(self, run):
        for line in run.output[::-1]:
            if line.startswith("[INFO] Model-checking result:"):
                if "UNREACHABLE" in line:
                    return result.RESULT_TRUE_PROP
                if "REACHABLE" in line:
                    return result.RESULT_FALSE_PROP
        return result.RESULT_ERROR
