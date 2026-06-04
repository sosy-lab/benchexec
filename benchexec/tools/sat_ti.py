# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

from benchexec import result
from benchexec.tools import template


class Tool(template.BaseTool2):
    """
    Tool-info module for sat solvers that were executed on the StarExec platform.
    """

    REQUIRED_PATHS = ["bin"]

    def executable(self, tool_locator):
        return tool_locator.find_executable("starexec_run_default", subdir="bin")

    def version(self, executable):
        return "TODO"

    def program_files(self, executable):
        return self._program_files_from_executable(
            executable, self.REQUIRED_PATHS, parent_dir=True
        )

    def name(self):
        return "SAT Solver"

    def working_directory(self, executable):
        from pathlib import Path

        return str(Path(executable).parent)

    def cmdline(self, executable, options, task, rlimits):
        return [executable, task.single_input_file, *options]

    def determine_result(self, run):
        for line in reversed(run.output):
            if line.startswith("s "):
                verdict = line.strip().partition(" ")[-1].strip().upper()
                if verdict.startswith("SATISFIABLE"):
                    return result.RESULT_TRUE_PROP
                elif verdict.startswith("UNSATISFIABLE"):
                    return result.RESULT_FALSE_PROP
                elif verdict.startswith("UNKNOWN"):
                    return result.RESULT_UNKNOWN
        return result.RESULT_ERROR
