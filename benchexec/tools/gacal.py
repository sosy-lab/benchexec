# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

from benchexec.tools.sv_benchmarks_util import get_data_model_from_task, ILP32, LP64
import benchexec.tools.template
import benchexec.result as result


class Tool(benchexec.tools.template.BaseTool2):
    """
    Tool info for GACAL.
    """

    def executable(self, tool_locator):
        return tool_locator.find_executable("run-gacal.py")

    def name(self):
        return "GACAL"

    def project_url(self):
        return "https://gitlab.com/bquiring/sv-comp-submission"

    def version(self, executable):
        return self._version_from_tool(executable)

    def cmdline(self, executable, options, task, rlimits):
        data_model_param = get_data_model_from_task(task, {ILP32: "32", LP64: "64"})
        if data_model_param and "--architecture" not in options:
            options += ["--architecture", data_model_param]

        return [executable] + options + list(task.input_files_or_identifier)

    def determine_result(self, run):
        for line in run.output:
            if "VERIFICATION_SUCCESSFUL" in line:
                return result.RESULT_TRUE_PROP
            elif "VERIFICATION_FAILED" in line:
                return result.RESULT_FALSE_REACH
            elif "COULD NOT PROVE ALL ASSERTIONS" in line or "UNKNOWN" in line:
                return result.RESULT_UNKNOWN
        return result.RESULT_UNKNOWN
