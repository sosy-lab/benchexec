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
    Tool info for JPF with symbolic extension (SPF)
    """

    REQUIRED_PATHS = [
        "jpf-core/bin/jpf",
        "jpf-core/build",
        "jpf-core/jpf.properties",
        "jpf-symbc/lib",
        "jpf-symbc/build",
        "jpf-symbc/jpf.properties",
        "jpf-sv-comp",
    ]

    def executable(self, tool_locator):
        return tool_locator.find_executable("jpf-sv-comp")

    def name(self):
        return "SPF"

    def project_url(self):
        return "https://github.com/symbolicpathfinder"

    def version(self, executable):
        output = self._version_from_tool(executable, arg="--version")
        first_line = output.splitlines()[0]
        return first_line.strip()

    def cmdline(self, executable, options, task, rlimits):
        options = options + ["--propertyfile", task.property_file]
        return [executable] + options + list(task.input_files)

    def determine_result(self, run):
        output = run.output
        # parse output
        status = result.RESULT_UNKNOWN

        for line in output:
            if "UNSAFE" in line:
                status = result.RESULT_FALSE_PROP
            elif "SAFE" in line:
                status = result.RESULT_TRUE_PROP

        return status
