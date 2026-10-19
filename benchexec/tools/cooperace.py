# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.tools.template
from benchexec import result


class Tool(benchexec.tools.template.BaseTool2):
    """
    Tool info for CoOpeRace.
    """

    def executable(self, tool_locator):
        return tool_locator.find_executable("cooperace")

    def name(self):
        return "CoOpeRace"

    def project_url(self):
        return "https://github.com/sws-lab/cooperace"

    def version(self, executable):
        return self._version_from_tool(executable, line_prefix="CoOpeRace")

    def cmdline(self, executable, options, task, rlimits):
        if task.property_file:
            options += ["--prop", task.property_file]
        if task.options is not None and "data_model" in task.options:
            options += ["--arch", task.options.get("data_model")]
        return [executable, *options, *task.input_files]

    def determine_result(self, run):
        if run.output:
            result_str = run.output[-1].strip()
            if result_str.startswith("CoOpeRace verdict: "):
                return result_str.removeprefix("CoOpeRace verdict: ")

        return result.RESULT_ERROR
