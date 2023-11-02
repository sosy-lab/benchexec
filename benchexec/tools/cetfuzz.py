# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

from benchexec.tools.sv_benchmarks_util import get_data_model_from_task, ILP32, LP64
import benchexec.tools.template
import benchexec.result as result


class Tool(benchexec.tools.template.BaseTool2):
    """
    cetfuzz
    """

    def executable(self, tool_locator):
        
        return tool_locator.find_executable("runTool.py", subdir=".")

    def version(self, executable):
        return self._version_from_tool(executable, use_stderr=True)

    def program_files(self, executable):
        return self._program_files_from_executable(
            executable, self.REQUIRED_PATHS, parent_dir=True
        )

    def name(self):
        return "cetfuzz"

    def cmdline(self, executable, options, task, rlimits):
        if task.property_file:
            options = options + ["--propertyFile", task.property_file]

        data_model_param = get_data_model_from_task(
            task, {ILP32: "32", LP64: "64"})
        if data_model_param and "--bit" not in options:
            options += ["--bit", data_model_param]

        return [executable] + options + [task.single_input_file]

    def determine_result(self, run):
        for line in run.output:
            if "TEST_SUIT_CREATED" in line:
                return result.RESULT_DONE
            elif "NOT_SUPPORTED" in line or "CETFUZZ_UNKNOWN" in line:
                return result.RESULT_UNKNOWN
        return result.RESULT_ERROR
