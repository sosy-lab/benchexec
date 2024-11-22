# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2024 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.tools.template
from benchexec.tools.sv_benchmarks_util import (
    handle_witness_of_task,
    TaskFilesConsidered,
)


class Tool(benchexec.tools.template.BaseTool2):
    """
    Tool info for the witness mapper (witnessmap)
    The goal of this tool, currently, is only to help run SV-COMP.
    """

    REQUIRED_PATHS = []

    def executable(self, tool_locator):
        return tool_locator.find_executable("witness_map.py")

    def name(self):
        return "witnessmap"

    def project_url(self):
        return "https://gitlab.com/sosy-lab/software/witnessmap"

    def version(self, executable):
        version_string = self._version_from_tool(executable)
        return version_string

    def cmdline(self, executable, options, task, rlimits):
        input_file, mapping_options = handle_witness_of_task(
            task, options, "--witness", TaskFilesConsidered.SINGLE_INPUT_FILE
        )

        return [
            executable,
            *options,
            *mapping_options,
            "--program",
            input_file[0],
        ]

    def get_value_from_output(self, output, identifier):
        for line in output:
            # Remove the log prefix containing the date, time and log level
            line_without_log_prefix = line.split("-", maxsplit=4)[-1].strip()
            if line_without_log_prefix.startswith(identifier):
                return line_without_log_prefix.split(":", maxsplit=1)[-1].strip()
        return None
