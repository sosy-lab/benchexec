# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.result as result
import benchexec.tools.template
from benchexec.tools.sv_benchmarks_util import ILP32, LP64, get_data_model_from_task


class Tool(benchexec.tools.template.BaseTool2):
    """
    Tool info for ESBMC-PathCov, a test-generation variant of ESBMC
    that combines fuzzing with bounded model checking.
    """

    REQUIRED_PATHS = [
        "pathcovc.py",
        "runtime.c",
        "search.py",
        "bounded.py",
        "esbmc.py",
        "solvers.py",
        "bin",
    ]

    def executable(self, tool_locator):
        return tool_locator.find_executable("pathcovc.py")

    def version(self, executable):
        return self._version_from_tool(executable)

    def name(self):
        return "ESBMC-PathCov"

    def project_url(self):
        return "https://gitlab.com/VishalKumarSwain/pathcovc"

    def cmdline(self, executable, options, task, rlimits):
        cmd = [executable, *options]
        if task.property_file:
            cmd += ["--property", task.property_file]
        data_model_param = get_data_model_from_task(
            task, {ILP32: "32bit", LP64: "64bit"}
        )
        if data_model_param and "--architecture" not in options:
            cmd += ["--architecture", data_model_param]
        if rlimits.cputime and "--time-limit" not in options:
            cmd += ["--time-limit", str(max(0.1, rlimits.cputime * 0.8))]
        return cmd + [task.single_input_file]

    def determine_result(self, run):
        if run.exit_code.value == 0 and any(
            line.strip() == "DONE" for line in run.output
        ):
            return result.RESULT_DONE
        return result.RESULT_UNKNOWN
