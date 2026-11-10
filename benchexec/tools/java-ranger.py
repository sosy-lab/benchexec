# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

from benchexec import result
from benchexec.tools.template import BaseTool2


class Tool(BaseTool2):
    """
    Tool info for Java Ranger that is based on the symbolic extension (SPF) of Java PathFinder (JPF)
    """

    def executable(self, tool_locator):
        return tool_locator.find_executable("jr-sv-comp")

    def name(self):
        return "Java Ranger"

    def project_url(self):
        return "https://github.com/vaibhavbsharma/java-ranger"

    def version(self, executable):
        output = self._version_from_tool(executable, arg="--version")
        first_line = output.splitlines()[0]
        return first_line.strip()

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
