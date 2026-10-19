# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2025 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

import benchexec.tools.template
from benchexec import result
from benchexec.tools.sv_benchmarks_util import (
    ILP32,
    LP64,
    get_data_model_from_task,
    get_non_witness_input_files_or_identifier,
)


class Tool(benchexec.tools.template.BaseTool2):
    """Tool info for VeriPick, which predicts the best verifier for a task and runs it."""

    REQUIRED_PATHS = ["src", "lib", ".fmweck_cache", ".fm-weck"]

    def executable(self, tool_locator):
        return tool_locator.find_executable("veripick")

    def name(self):
        return "VeriPick"

    def project_url(self):
        return "https://gitlab.com/sosy-lab/software/veripick"

    def version(self, executable):
        return self._version_from_tool(executable, arg="--version")

    def cmdline(self, executable, options, task, rlimits):
        if task.property_file:
            options = options + ["--spec", Path(task.property_file).stem]

        data_model = get_data_model_from_task(task, {ILP32: "ILP32", LP64: "LP64"})
        if data_model and "--data-model" not in options:
            options = options + ["--data-model", data_model]

        limit = rlimits.walltime or rlimits.cputime
        if limit and "--time-limit" not in options:
            options = options + ["--time-limit", str(limit)]

        if "--statistics" not in options:
            options = options + ["--statistics"]

        input_files = get_non_witness_input_files_or_identifier(task)
        return [executable, *options, *input_files]

    def determine_result(self, run):
        """Read the verdict VeriPick reports.

        VeriPick asks the tool info of the verifier it ran, so the verdict is
        already a BenchExec result and is passed on unchanged.
        """
        for line in reversed(run.output):
            stripped = line.strip()
            if stripped.startswith("Result:"):
                verdict = stripped[len("Result:") :].strip()
                if verdict in (None, "", "None"):
                    return result.RESULT_UNKNOWN
                return verdict
            if stripped.startswith("Error during analysis:"):
                return (
                    result.RESULT_ERROR
                    + " ("
                    + stripped[len("Error during analysis:") :].strip()[:40]
                    + ")"
                )

        return result.RESULT_ERROR

    def get_value_from_output(self, output, identifier):
        for line in output:
            stripped = line.strip()
            if stripped.startswith(identifier):
                return stripped[len(identifier) :].strip()
        return None
