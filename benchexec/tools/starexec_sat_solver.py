# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import os

import benchexec.result as result
import benchexec.tools.template


class Tool(benchexec.tools.template.BaseTool2):
    """
    Generic tool-info for SAT Competition solvers distributed as StarExec
    archives with a single starexec_run_default launcher script in a "bin/"
    subdirectory.
    """

    REQUIRED_PATHS = ["bin"]

    def executable(self, tool_locator):
        return tool_locator.find_executable("starexec_run_default", subdir="bin")

    def program_files(self, executable):
        return self._program_files_from_executable(
            executable, self.REQUIRED_PATHS, parent_dir=True
        )

    def name(self):
        return "StarExec SAT Solver"

    def working_directory(self, executable):
        return os.path.dirname(executable)

    def cmdline(self, executable, options, task, rlimits):
        return [executable, task.single_input_file, *options]

    def determine_result(self, run):
        for line in reversed(run.output):
            if line.startswith("s "):
                verdict = line.removeprefix("s ").strip().upper()
                if verdict.startswith("SATISFIABLE"):
                    return result.RESULT_TRUE_PROP
                elif verdict.startswith("UNSATISFIABLE"):
                    return result.RESULT_FALSE_PROP
                elif verdict.startswith("UNKNOWN"):
                    return result.RESULT_UNKNOWN
        return result.RESULT_ERROR
