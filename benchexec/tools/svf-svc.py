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
    Tool info for SVF-SVC: a framework for static value-flow analysis.
    Specifically this tool is a wrapper around SVF to make it work with SV-COMP.
    - SVF: https://github.com/SVF-tools/SVF
    """

    REQUIRED_PATHS = ["svf", "include_replace.c"]

    def executable(self, tool_locator):
        return tool_locator.find_executable("svf_run.py")

    def name(self):
        return "SVF-SVC"

    def project_url(self):
        return "https://github.com/Lasagnenator/svf-svc-comp"

    def version(self, executable):
        return self._version_from_tool(executable, "--version")

    def cmdline(self, executable, options, task, rlimits):
        data_model_param = get_data_model_from_task(task, {ILP32: "32", LP64: "64"})
        if data_model_param and data_model_param not in options:
            options += ["--bits", data_model_param]

        if task.property_file:
            options += ["--prop", task.property_file]

        if rlimits.cputime:
            options += ["--time-limit", str(rlimits.cputime)]

        return [executable] + options + [task.single_input_file]

    def determine_result(self, run):
        for line in run.output:
            if line.startswith("REACH Incorrect"):
                return result.RESULT_FALSE_REACH
            elif line.startswith("MEMORY Incorrect"):
                # SVF-SVC does not currently distinguish between memory safety types.
                return result.RESULT_FALSE_PROP
            elif line.startswith("OVERFLOW Incorrect"):
                return result.RESULT_FALSE_OVERFLOW
            elif "Incorrect" in line:
                return result.RESULT_FALSE_PROP
            elif "Correct" in line:
                return result.RESULT_TRUE_PROP
            elif line.startswith("Unknown"):
                return result.RESULT_UNKNOWN
            elif line.startswith("ERROR("):
                # This will always be a single word error.
                return line

        # Not matching any means something bad happened.
        return result.RESULT_ERROR
