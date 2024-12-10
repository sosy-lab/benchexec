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
    Tool info for rIC3
    """

    def executable(self, tool_locator):
        return tool_locator.find_executable("rIC3")

    def name(self):
        return "rIC3"

    def version(self, executable):
        version_string = self._version_from_tool(executable, line_prefix="rIC3 ")
        commit_hash = self._version_from_tool(executable, line_prefix="commit_hash:")
        if commit_hash:
            # Different commits of rIC3 could have the same version number.
            # Therefore, the commit hash is appended to get a more precise version information.
            version_string += f" ({commit_hash})"
        return version_string

    def project_url(self):
        return "https://github.com/gipsyh/rIC3"

    def cmdline(self, executable, options, task, rlimits):
        return [executable] + options + [task.single_input_file]

    def determine_result(self, run):
        for line in run.output[::-1]:
            # skip the lines that do not contain verification result
            if not line.startswith("result:"):
                continue
            if "true" in line:
                return result.RESULT_TRUE_PROP
            elif "false" in line:
                return result.RESULT_FALSE_PROP
        return result.RESULT_ERROR
