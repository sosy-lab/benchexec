# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.result as result
from benchexec.tools.template import BaseTool2


class Tool(BaseTool2):
    REQUIRED_PATHS = [
        "GraalWrapper",
        "nodes",
        "libs",
        "svHelpers",
        "run_dasa.sh",
        "run_sv-comp.py",
        "test.py",
        "Version.py",
        ".venv_dasa",
    ]
    """
    Tool info module for DASA, a static differentiable symbolic analyzer.
    DASA is currently being developed by the Institute for IT Security at the University of Luebeck.
    """

    def executable(self, tool_locator):
        return tool_locator.find_executable("run_dasa.sh")

    def name(self):
        return "DASA"

    def project_url(self):
        return "https://www.its.uni-luebeck.de/en/research/tools/dasa/"

    def version(self, executable):
        return self._version_from_tool(executable, arg="-v")

    def cmdline(self, executable, options, task, rlimits):
        cmd = [executable] + options
        if task.property_file:
            cmd.append(task.property_file)
        return cmd + list(task.input_files)

    def determine_result(self, run):
        if run.output.any_line_contains("DASA_VERDICT: VIOLATION"):
            return result.RESULT_FALSE_PROP
        elif run.output.any_line_contains("DASA_VERDICT: UNKNOWN"):
            return result.RESULT_UNKNOWN

        return result.RESULT_ERROR
