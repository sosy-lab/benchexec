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
    Tool info for JayHorn.
    """

    REQUIRED_PATHS = [
        "jayhorn.jar",
        "EnumEliminator-assembly-0.1.jar",
    ]

    def executable(self, tool_locator):
        return tool_locator.find_executable("jayhorn")

    def version(self, executable):
        return self._version_from_tool(executable)

    def name(self):
        return "JayHorn"

    def project_url(self):
        return "https://github.com/jayhorn/jayhorn"

    def cmdline(self, executable, options, task, rlimits):
        if task.property_file:
            options = options + ["--propertyfile", task.property_file]

        return [executable] + options + list(task.input_files)

    def determine_result(self, run):
        # parse output
        status = result.RESULT_UNKNOWN

        for line in run.output:
            if "UNSAFE" in line:
                status = result.RESULT_FALSE_PROP
            elif "SAFE" in line:
                status = result.RESULT_TRUE_PROP

        return status
