# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
# SPDX-FileCopyrightText: 2024 Tomas Dacik <idacik@fit.vut.cz>
#
# SPDX-License-Identifier: Apache-2.0


from benchexec import result
from benchexec.tools.template import BaseTool2
from benchexec.tools.sv_benchmarks_util import get_data_model_from_task, ILP32, LP64


class Tool(BaseTool2):
    """
    Tool info for RacerF, a data race detection plugin of Frama-C.
    """

    def name(self):
        return "RacerF"

    def project_url(self):
        return "https://github.com/TDacik/Deadlock_Racer"

    def version(self, executable):
        return self._version_from_tool(executable)

    def executable(self, tool_locator):
        return tool_locator.find_executable("racerf-sv.py")

    def cmdline(self, executable, options, task, rlimits):
        machdep = get_data_model_from_task(
            task, {ILP32: "gcc_x86_32", LP64: "gcc_x86_64"}
        )
        machdep_opt = ["-machdep", machdep] if machdep is not None else []

        return [executable] + machdep_opt + options + list(task.input_files)

    def determine_result(self, run):
        if run.exit_code:
            return result.RESULT_ERROR

        if run.output.any_line_contains("The result may be imprecise"):
            return result.RESULT_UNKNOWN

        if run.output.any_line_contains("Data race (must)"):
            return result.RESULT_FALSE_PROP

        if run.output.any_line_contains("Data race (may)"):
            return result.RESULT_UNKNOWN

        if run.output.any_line_contains("No data races found"):
            return result.RESULT_TRUE_PROP

        return result.RESULT_ERROR
