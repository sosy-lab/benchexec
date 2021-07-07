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
    VeriFuzz
    """

    def executable(self, tool_locator):
        return tool_locator.find_executable("verifuzz.py", subdir="scripts")

    def version(self, executable):
        return self._version_from_tool(executable, use_stderr=True)

    def program_files(self, executable):
        return self._program_files_from_executable(
            executable, self.REQUIRED_PATHS, parent_dir=True
        )

    def name(self):
        return "VeriFuzz"

    def cmdline(self, executable, options, task, rlimits):
        if task.property_file:
            options = options + ["--propertyFile", task.property_file]

        data_model_param = get_data_model_from_task(task, {ILP32: "32", LP64: "64"})
        if data_model_param and "--bit" not in options:
            options += ["--bit", data_model_param]

        return [executable] + options + [task.single_input_file]

    def determine_result(self, run):
        for line in run.output:
            if "COVER(error-call)" in line:
                return result.RESULT_DONE
            elif "COVER(branches)" in line:
                return result.RESULT_DONE
            elif "VERIFUZZ_VERIFICATION_SUCCESSFUL" in line:
                return result.RESULT_TRUE_PROP
            elif "VERIFUZZ_VERIFICATION_FAILED" in line:
                return result.RESULT_FALSE_REACH
            elif "FALSE(unreach-call)" in line:
                return result.RESULT_FALSE_REACH
            elif "FALSE(no-overflow)" in line:
                return result.RESULT_FALSE_OVERFLOW
            elif "FALSE(termination)" in line:
                return result.RESULT_FALSE_TERMINATION
            elif "FALSE(valid-deref)" in line:
                return result.RESULT_FALSE_DEREF
            elif "FALSE(valid-free)" in line:
                return result.RESULT_FALSE_FREE
            elif "FALSE(valid-memtrack)" in line:
                return result.RESULT_FALSE_MEMTRACK
            elif "NOT SUPPORTED" in line or "VERIFUZZ_UNKNOWN" in line:
                return result.RESULT_UNKNOWN
        return result.RESULT_ERROR
