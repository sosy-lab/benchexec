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
    Tool info for SVF: a framework for static value-flow analysis.
    Specifically this tool is a wrapper around SVF to make it work with SV-COMP.
    - Project URL: https://github.com/Lasagnenator/svf-svc-comp
    - SVF: https://github.com/SVF-tools/SVF
    - SVF version used: SVF-3.0
    """

    REQUIRED_PATHS = ["svf", "include_replace.c"]

    def executable(self, tool_locator):
        return tool_locator.find_executable("svf_run.py")

    def name(self):
        return "SVF"

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
        return [executable] + options + [task.single_input_file]

    def determine_result(self, run):
        good_exit = False
        verified = True

        for line in run.output:
            if line.startswith("Correct"):
                good_exit |= True
                verified &= True
            elif line.startswith("Incorrect"):
                good_exit |= True
                verified &= False

        if not good_exit:
            return result.RESULT_UNKNOWN
        elif verified:
            return result.RESULT_TRUE_PROP
        else:
            return result.RESULT_FALSE_PROP
