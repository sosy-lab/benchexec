# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2022 Raphaël Monat
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.result as result
import benchexec.tools.template
from benchexec.tools.sv_benchmarks_util import (
    TaskFilesConsidered,
    handle_witness_of_task,
)


class Tool(benchexec.tools.template.BaseTool2):
    """
    Tool info for Mopsa.
    """

    def executable(self, tool_locator):
        return tool_locator.find_executable("mopsa-sv-comp", subdir="bin/")

    def version(self, executable):
        return self._version_from_tool(executable)

    def name(self):
        return "Mopsa"

    def project_url(self):
        return "https://gitlab.com/mopsa/mopsa-analyzer/"

    def cmdline(self, executable, options, task, rlimits):
        input_files, witness_options = handle_witness_of_task(
            task,
            options,
            "--validate_yaml_witness",
            TaskFilesConsidered.INPUT_FILES,
        )

        cmd = [executable, "--program"] + input_files + witness_options
        if task.options is not None and "data_model" in task.options:
            cmd += ["--data_model", task.options.get("data_model")]
        if task.property_file:
            cmd += ["--property", task.property_file]
        return cmd + list(options)

    def determine_result(self, run):
        if run.was_timeout:
            return result.RESULT_TIMEOUT
        r = run.output[-1] or run.output[-2]  # last non-empty line
        r = r.lower()
        if r.startswith("true"):
            return result.RESULT_TRUE_PROP
        elif r.startswith("unknown"):
            return result.RESULT_UNKNOWN
        elif r.startswith("error"):
            return result.RESULT_ERROR + r[len("ERROR") :]
        else:
            return result.RESULT_ERROR + "(unknown)"
