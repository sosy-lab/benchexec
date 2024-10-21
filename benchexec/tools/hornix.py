# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
# SPDX-FileCopyrightText: 2024 Jan Kofron <jan.kofron@d3s.mff.cuni.cz>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec
import benchexec.result as result


class Tool(benchexec.tools.template.BaseTool2):
    """
    Info object for the tool Hornix.
    """

    REQUIRED_PATHS = ["."]

    def executable(self, tool_locator):
        return tool_locator.find_executable("hornix")

    def version(self, executable):
        return self._version_from_tool(executable, arg="--version")

    def name(self):
        """The human-readable name of the tool."""
        return "Hornix"

    def project_url(self):
        return "https://github.com/d3sformal/hornix"

    def determine_result(self, run):
        if len(run.output) != 1:
            return result.RESULT_ERROR
        line = run.output[0].strip()
        if "sat" == line:
            return result.RESULT_TRUE_PROP
        elif "unsat" == line:
            return result.RESULT_FALSE_REACH
        elif "unknown" == line:
            return result.RESULT_UNKNOWN
        else:
            return result.RESULT_ERROR
