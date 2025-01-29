# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.tools.template
import benchexec.result as result


class Tool(benchexec.tools.template.BaseTool2):
    """
    Tool info for MLB
    """

    def executable(self, tool_locator):
        return tool_locator.find_executable("run.sh")

    def version(self, executable):
        return self._version_from_tool(executable, arg="-version")

    def name(self):
        return "MLB"

    def project_url(self):
        return "https://github.com/MLB-SE/Experiment"

    def cmdline(self, executable, options, task, rlimits):
        cmd = [executable]
        if options:
            cmd = cmd + options
        if task.property_file:
            cmd.append(task.property_file)
        return cmd + list(task.input_files_or_identifier)

    def determine_result(self, run):
        # parse output
        status = result.RESULT_ERROR
        for line in run.output:
            if "==> FALSE" in line:
                status = result.RESULT_FALSE_PROP
            elif "==> TRUE" in line:
                status = result.RESULT_TRUE_PROP
            elif "==> UNKNOWN" in line:
                status = result.RESULT_UNKNOWN

        return status
