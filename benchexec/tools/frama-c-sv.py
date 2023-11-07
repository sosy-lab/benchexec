# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.result
import benchexec.tools.template
from collections.abc import Mapping


class Tool(benchexec.tools.template.BaseTool2):
    """
    Tool info for Frama-C with a wrapper for usage in the SVCOMP.
    """

    REQUIRED_PATHS = ["."]
    _TOOL_NAME = "frama-c-sv"
    _SCRIPT_NAME = _TOOL_NAME + ".py"

    def executable(self, tool_locator):
        return tool_locator.find_executable(Tool._SCRIPT_NAME)

    def version(self, executable):
        return self._version_from_tool(executable, line_prefix="frama-c-sv version ")

    def name(self):
        return Tool._TOOL_NAME

    def project_url(self):
        return "https://gitlab.com/sosy-lab/software/frama-c-sv"

    def cmdline(self, executable, options, task, rlimits):
        cmd = [executable, "--program"] + list(task.input_files)
        if task.property_file:
            cmd += ["--property", task.property_file]
        if isinstance(task.options, Mapping) and "data_model" in task.options:
            cmd += ["--datamodel", task.options["data_model"]]
        cmd += options
        return cmd

    def determine_result(self, run):
        lastline = run.output[-1]
        if lastline.startswith("INFO\tRESULT\t"):
            return lastline.split("\t", maxsplit=3)[-1]
        elif lastline.startswith("INFO:RESULT:"):
            return lastline.split(":", maxsplit=2)[-1]
        else:
            return benchexec.result.RESULT_ERROR
