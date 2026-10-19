# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
# SPDX-FileCopyrightText: 2026 Xinyu Zhang
# SPDX-License-Identifier: Apache-2.0

from benchexec import result
from benchexec.tools.sv_benchmarks_util import ILP32, LP64, get_data_model_from_task
from benchexec.tools.template import BaseTool2


class Tool(BaseTool2):
    """Tool info for C2Btor."""

    REQUIRED_PATHS = [
        "bin/",
        "build/bin/c2btor",
        "checkers/carat/build/carat",
        "checkers/carat/deps/btor2tools/build/bin/btorsim",
        "scripts/",
    ]

    def executable(self, tool_locator):
        return tool_locator.find_executable("c2btor-verify")

    def name(self):
        return "C2Btor"

    def project_url(self):
        return "https://github.com/westtide/c2btor"

    def version(self, executable):
        return self._version_from_tool(executable)

    def cmdline(self, executable, options, task, rlimits):
        options = list(options)
        if task.property_file:
            options += ["--property", task.property_file]
        data_model = get_data_model_from_task(task, {ILP32: ILP32, LP64: LP64})
        if data_model and "--data-model" not in options:
            options += ["--data-model", data_model]
        return [executable, task.single_input_file, *options]

    def determine_result(self, run):
        if run.exit_code or run.was_terminated:
            return result.RESULT_ERROR
        verdicts = {
            "Verification result: TRUE": result.RESULT_TRUE_PROP,
            "Verification result: FALSE(unreach-call)": result.RESULT_FALSE_REACH,
            "Verification result: UNKNOWN": result.RESULT_UNKNOWN,
            "Verification result: ERROR": result.RESULT_ERROR,
        }
        for line in reversed(run.output):
            if line in verdicts:
                return verdicts[line]
        return result.RESULT_ERROR
