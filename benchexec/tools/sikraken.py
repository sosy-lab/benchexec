# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

from benchexec.tools.sv_benchmarks_util import get_data_model_from_task, ILP32, LP64
import benchexec.tools.template


class Tool(benchexec.tools.template.BaseTool2):
    """
    BenchExec tool-info for Sikraken
    """

    def name(self):
        return "Sikraken"

    def project_url(self):
        return "https://github.com/echancrure/Sikraken"

    def executable(self, tool_locator):
        return tool_locator.find_executable("sikraken.sh", subdir="bin")

    def version(self, executable):
        return self._version_from_tool(executable, "-v")

    def cmdline(self, executable, options, task, rlimits):
        data_model_param = get_data_model_from_task(task, {ILP32: "-m32", LP64: "-m64"})
        if data_model_param and data_model_param not in options:
            options += [data_model_param]
        return [executable] + options + [task.single_input_file]
