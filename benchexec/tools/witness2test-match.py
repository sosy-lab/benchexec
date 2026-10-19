# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2026 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import re

import benchexec.tools.template
from benchexec import result
from benchexec.tools.sv_benchmarks_util import (
    ILP32,
    LP64,
    TaskFilesConsidered,
    get_data_model_from_task,
    handle_witness_of_task,
)


class Tool(benchexec.tools.template.BaseTool2):
    """
    Validate violation witnesses by executing C tests with witness2test-match.

    Supports C tasks with ILP32 or LP64 data models, passed via --model.
    Passes the task's property file via --property.
    Accepts witnesses via --witness or the task's witness_input_file option.
    """

    def executable(self, tool_locator):
        return tool_locator.find_executable("witness2test-match", subdir="bin")

    def name(self):
        return "witness2test-match"

    def project_url(self):
        return "https://github.com/lembergerth/witness2test-match"

    def version(self, executable):
        return self._version_from_tool(
            executable, line_prefix="witness2test-match version "
        )

    def cmdline(self, executable, options, task, rlimits):
        def option_present(option):
            return any(
                argument.partition("=")[0] == f"--{option}" for argument in options
            )

        data_model = get_data_model_from_task(task, {ILP32: "ILP32", LP64: "LP64"})
        if data_model:
            if option_present("model"):
                raise benchexec.tools.template.UnsupportedFeatureException(
                    "Data model provided in tool options and via task file."
                )
            options = [*options, "--model", data_model]

        if task.property_file:
            if option_present("property"):
                raise benchexec.tools.template.UnsupportedFeatureException(
                    "Property file provided in tool options and via task file."
                )
            options = [*options, "--property", task.property_file]

        input_files, witness_options = handle_witness_of_task(
            task, options, "--witness", TaskFilesConsidered.SINGLE_INPUT_FILE
        )
        return [executable, *options, *witness_options, "--program", *input_files]

    def determine_result(self, run):
        status = result.RESULT_UNKNOWN
        for line in run.output:
            confirmed = re.match(r"Verdict: Confirmed (\w\S*)", line)
            if confirmed:
                return f"{result.RESULT_FALSE_PROP}({confirmed.group(1)})"

            if line.lower().startswith(("error", "panic:", "fatal error:")):
                status = result.RESULT_ERROR
        return status
