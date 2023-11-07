# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.tools.template
from benchexec.tools.sv_benchmarks_util import get_data_model_from_task, ILP32, LP64


class Tool(benchexec.tools.template.BaseTool2):
    """
    Tool info for LibKluzzer.
    """

    def program_files(self, executable):
        return self._program_files_from_executable(
            executable, self.REQUIRED_PATHS, parent_dir=True
        )

    def executable(self, tool_locator):
        return tool_locator.find_executable("LibKluzzer", subdir="bin")

    def version(self, executable):
        return self._version_from_tool(executable)

    def name(self):
        return "LibKluzzer"

    def project_url(self):
        return "http://unihb.eu/kluzzer"

    def cmdline(self, executable, options, task, rlimits):
        data_model_param = get_data_model_from_task(task, {ILP32: None, LP64: "--64"})
        if data_model_param and data_model_param not in options:
            options += [data_model_param]

        return [executable, *options, *task.input_files_or_identifier]
