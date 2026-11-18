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
        # witness2test-match prints its verdict as the last line, after the
        # output of the tested program. Reading the output from the end, the
        # first verdict line decides the result, even if error or crash lines
        # follow it. Without a verdict line, the last error or crash in the output
        # decides the type of error that is reported.
        error = None
        for line in reversed(run.output):
            confirmed = re.match(r"Verdict: Confirmed (\w\S*)", line)
            if confirmed:
                return f"{result.RESULT_FALSE_PROP}({confirmed.group(1)})"
            if line.startswith("Verdict: Confirmed"):
                # We don't know which property was confirmed,
                # but we know verdict 'false'.
                return result.RESULT_FALSE_PROP
            if line.startswith("Verdict: "):
                return result.RESULT_UNKNOWN
            if error is None:
                error = self._maybe_get_error_of_line(line)
        return error or result.RESULT_ERROR

    def _maybe_get_error_of_line(self, line):
        if line.startswith("witness2test-match error"):
            tagged = re.match(
                r"witness2test-match error \[([a-z][a-z0-9 -]*)\]: ", line
            )
            if tagged:
                return f"{result.RESULT_ERROR}({tagged.group(1)})"
            return result.RESULT_ERROR

        # The below is Go-emitted error messages
        if line.lower().startswith("fatal error:"):
            return f"{result.RESULT_ERROR}(fatal error)"
        if line.lower().startswith("panic:"):
            return f"{result.RESULT_ERROR}(panic)"
        return None
