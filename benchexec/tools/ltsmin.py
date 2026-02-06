# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2025 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.result as result
from benchexec.tools.template import BaseTool2


class Tool(BaseTool2):
    """
    Wrapper for LTSmin.
    """

    REQUIRED_PATHS = ["bin/", "include/", "share/"]

    def executable(self, tool_locator):
        return tool_locator.find_executable("ltsmin-reduce", subdir="bin")

    def name(self):
        return "LTSmin"

    def project_url(self):
        return "https://ltsmin.utwente.nl/"

    def version(self, executable):
        return self._version_from_tool(executable, line_prefix="v")

    def cmdline(self, executable, options, task: BaseTool2.Task, rlimits):
        from pathlib import Path

        real_executable = options.pop(0) if len(options) > 0 else executable
        real_executable = str(Path(executable).parent / real_executable)

        return [real_executable] + options + [task.single_input_file]

    def determine_result(self, run):
        if run.exit_code.signal != 0:
            return result.RESULT_ERROR

        return result.RESULT_DONE
