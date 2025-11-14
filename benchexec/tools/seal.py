# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
# SPDX-FileCopyrightText: 2025 Tomas Brablec <xbrabl04@stud.fit.vutbr.cz>
#
# SPDX-License-Identifier: Apache-2.0


from benchexec import result
from benchexec.tools.template import BaseTool2
from benchexec.tools.sv_benchmarks_util import get_data_model_from_task, ILP32, LP64


class Tool(BaseTool2):
    def name(self):
        return "SEAL"

    def project_url(self):
        return "https://github.com/pepega007xd/seal"

    def version(self, executable):
        return self._version_from_tool(executable)

    def executable(self, tool_locator):
        return tool_locator.find_executable("seal-entrypoint.py")

    def cmdline(self, executable, options, task, rlimits):
        machdep = get_data_model_from_task(
            task, {ILP32: "gcc_x86_32", LP64: "gcc_x86_64"}
        )
        machdep_opt = ["-machdep", machdep] if machdep is not None else []

        return [executable] + machdep_opt + options + [task.single_input_file]

    def determine_result(self, run):
        if run.exit_code.value != 0:
            return result.RESULT_ERROR

        if run.output.any_line_contains("Unknown_result"):
            return result.RESULT_UNKNOWN

        if run.output.any_line_contains("Invalid_deref"):
            return result.RESULT_FALSE_DEREF

        if run.output.any_line_contains("Invalid_free"):
            return result.RESULT_FALSE_FREE

        if run.output.any_line_contains("Invalid_memtrack"):
            return result.RESULT_FALSE_MEMTRACK

        if run.output.any_line_contains("Successful_verification"):
            return result.RESULT_TRUE_PROP

        return result.RESULT_ERROR
