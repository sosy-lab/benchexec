# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.result as result
import benchexec.tools.template
import benchexec.util as util


class Tool(benchexec.tools.template.BaseTool2):
    """
    Tool info for COASTAL
    """

    REQUIRED_PATHS = ["coastal", "coastal-sv-comp"]

    def executable(self, tool_locator):
        return tool_locator.find_executable("coastal-sv-comp")

    def name(self):
        return "COASTAL"

    def project_url(self):
        return "http://www.cs.sun.ac.za/coastal/"

    def version(self, executable):
        output = self._version_from_tool(executable, arg="--version")
        first_line = output.splitlines()[0]
        return first_line.strip()

    def cmdline(self, executable, options, task, rlimits):
        options = options + ["--propertyfile", task.property_file]
        return [executable] + options + list(task.input_files_or_identifier)

    def determine_result(self, run):
        # parse output
        status = result.RESULT_UNKNOWN

        for line in run.output:
            if "UNSAFE" in line:
                status = result.RESULT_FALSE_PROP
            elif "SAFE" in line:
                status = result.RESULT_TRUE_PROP

        return status
