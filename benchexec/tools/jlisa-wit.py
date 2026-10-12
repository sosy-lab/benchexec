# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2026 UniVE-SSV
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
    Tool info for jlisa-wit.
    """

    def executable(self, tool_locator):
        return tool_locator.find_executable("jlisa-wit")

    def version(self, executable):
        return self._version_from_tool(executable)

    def name(self):
        return "jlisa-wit"

    def project_url(self):
        return "https://github.com/lisa-analyzer/jlisa-witness-validator"

    def cmdline(self, executable, options, task, rlimits):
        input_files, witness_options = handle_witness_of_task(
            task, options, "--witness", TaskFilesConsidered.INPUT_FILES
        )
        cmd = [executable] + options + witness_options
        if task.property_file:
            cmd += ["--property", task.property_file]
        return cmd + list(input_files)

    def determine_result(self, run):
        for line in reversed(run.output):
            if line.startswith("Witness Correct"):
                return result.RESULT_FALSE_PROP
            if line.startswith("Witness Spurious"):
                return result.RESULT_TRUE_PROP
            if line.startswith("Could not validate"):
                return result.RESULT_UNKNOWN
        return result.RESULT_ERROR
