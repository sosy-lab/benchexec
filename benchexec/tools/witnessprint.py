# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2026 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.tools.template
from benchexec import result
from benchexec.tools.sv_benchmarks_util import (
    TaskFilesConsidered,
    handle_witness_of_task,
)


class Tool(benchexec.tools.template.BaseTool2):
    """
    Tool info for the witness printer (witnessprint).
    It prints the witness of a validation task as plain text,
    such that the witness is shown in the log file of the run.
    """

    REQUIRED_PATHS = []

    def executable(self, tool_locator):
        return tool_locator.find_executable("witness_print.py")

    def name(self):
        return "witnessprint"

    def project_url(self):
        return "https://gitlab.com/sosy-lab/software/witnessprint"

    def version(self, executable):
        return self._version_from_tool(executable)

    def cmdline(self, executable, options, task, rlimits):
        input_files, witness_options = handle_witness_of_task(
            task,
            options,
            "--witness",
            TaskFilesConsidered.INPUT_FILES_OR_IDENTIFIER,
        )

        return [executable, *options, *witness_options, *input_files]

    def determine_result(self, run):
        if run.exit_code.value == 1:
            return result.RESULT_ERROR + " (cannot read witness)"
        return result.RESULT_DONE
