# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.tools.template
from benchexec import result
from benchexec.tools.sv_benchmarks_util import ILP32, LP64, get_data_model_from_task


class Tool(benchexec.tools.template.BaseTool2):
    """
    Tool info for Map2Check as a Test-Comp test generator
    (https://github.com/hbgit/Map2Check).

    Separate from map2check.py, the SV-COMP verification adaptor: this one
    produces a test suite and lets the validators score it, so the run
    result is only whether the tool ran.

    Supports the properties coverage-error-call and coverage-branches; the
    tool rejects any other. Passes the task's data model (--data-model) and
    the time limit (--budget, the tool stops shortly before it so that the
    suite is complete). The test suite is written to ./test-suite/.
    """

    REQUIRED_PATHS = [
        "map2check",
        "map2check-testcomp-wrapper.py",
        "bin",
        "include",
        "lib",
    ]

    def executable(self, tool_locator):
        return tool_locator.find_executable("map2check-testcomp-wrapper.py")

    def program_files(self, executable):
        return self._program_files_from_executable(executable, self.REQUIRED_PATHS)

    def version(self, executable):
        # Map2Check prints "v9.0.0-Songbirds:2026-10-13".
        return self._version_from_tool(executable).removeprefix("v")

    def name(self):
        return "Map2Check"

    def project_url(self):
        return "https://github.com/hbgit/Map2Check"

    def cmdline(self, executable, options, task, rlimits):
        if task.property_file is None:
            raise benchexec.tools.template.UnsupportedFeatureException(
                "Map2Check needs a property file to know what to cover"
            )

        cmd = [executable, "-p", task.property_file]
        data_model = get_data_model_from_task(task, {ILP32: "ILP32", LP64: "LP64"})
        if data_model:
            cmd += ["--data-model", data_model]
        # The wrapper stops the tool shortly before this budget, so that the
        # suite is written before the run is killed.
        budget = rlimits.walltime or rlimits.cputime
        if budget:
            cmd += ["--budget", str(budget)]
        return cmd + list(options) + [task.single_input_file]

    def determine_result(self, run):
        if run.was_timeout or run.exit_code.value == 0:
            return result.RESULT_DONE
        return result.RESULT_ERROR
