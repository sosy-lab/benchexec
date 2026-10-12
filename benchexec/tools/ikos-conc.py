# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2026 Ronghui Ruan
#
# SPDX-License-Identifier: Apache-2.0

from benchexec import result
from benchexec.tools.sv_benchmarks_util import ILP32, LP64, get_data_model_from_task
from benchexec.tools.template import BaseTool2


class Tool(BaseTool2):
    """IKOS-ConC's packaged data-race verification and witness entry point.

    The executable handles property validation, analysis configuration, and
    witness generation. Only a definite race is reported as false; inconclusive
    analysis is unknown, and unsuccessful execution is an error.
    """

    REQUIRED_PATHS = ["bin", "lib", "libexec", "llvm", "include"]

    def name(self):
        return "ikos-conc"

    def executable(self, tool_locator):
        return tool_locator.find_executable("svcomp_witness.py", subdir="bin")

    def program_files(self, executable):
        return self._program_files_from_executable(
            executable, self.REQUIRED_PATHS, parent_dir=True
        )

    def version(self, executable):
        return self._version_from_tool(executable, line_prefix="ikos")

    def cmdline(self, executable, options, task, rlimits):
        data_model = get_data_model_from_task(task, {ILP32: ILP32, LP64: LP64})
        model_options = ["--data-model", data_model] if data_model else []
        property_options = (
            ["--property", task.property_file] if task.property_file else []
        )
        return [
            executable,
            *options,
            *model_options,
            *property_options,
            task.single_input_file,
        ]

    def determine_result(self, run):
        if run.exit_code.value != 0:
            return result.RESULT_ERROR
        if "The program is definitely UNSAFE" in run.output:
            return result.RESULT_FALSE_DATARACE
        if (
            "The program is UNKNOWN" in run.output
            or "The program is potentially UNSAFE" in run.output
        ):
            return result.RESULT_UNKNOWN
        if "The program is SAFE" in run.output:
            return result.RESULT_TRUE_PROP
        return result.RESULT_UNKNOWN
