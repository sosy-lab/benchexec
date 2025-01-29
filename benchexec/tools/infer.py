# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.tools.template
from collections.abc import Mapping
import benchexec.result as result


class Tool(benchexec.tools.template.BaseTool2):
    """
    Tool info for Infer with a wrapper for usage in the SVCOMP.
    """

    def executable(self, tool_locator):
        return tool_locator.find_executable("infer-wrapper.py")

    def version(self, executable):
        return self._version_from_tool(executable)

    def name(self):
        return "Infer-SV"

    def project_url(self):
        return "https://fbinfer.com/"

    def cmdline(self, executable, options, task, rlimits):
        cmd = [executable, "--program", task.single_input_file]
        if task.property_file:
            cmd += ["--property", task.property_file]
        if isinstance(task.options, Mapping) and "data_model" in task.options:
            cmd += ["--datamodel", task.options["data_model"]]
        return cmd

    def determine_result(self, run):
        if not run.output:
            return result.RESULT_ERROR
        last_line = run.output[-1]
        if last_line.startswith("Result:"):
            run_result = last_line.split(":", maxsplit=2)[-1]
            if run_result == "true":
                return result.RESULT_TRUE_PROP
            if run_result.startswith("false"):
                return run_result
            if run_result == "unknown":
                return result.RESULT_UNKNOWN
        return result.RESULT_ERROR
