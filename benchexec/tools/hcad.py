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
    Tool-info for SAT-comp solvers shipped with two StarExec run scripts
    (starexec_run_pbva / starexec_run_bva), used by hCaD and hKis.
    """

    REQUIRED_PATHS = ["bin"]

    def executable(self, tool_locator):
        return tool_locator.find_executable("starexec_run_pbva", subdir="bin")

    def program_files(self, executable):
        return self._program_files_from_executable(
            executable, self.REQUIRED_PATHS, parent_dir=True
        )

    def name(self):
        return "hCaD"

    def working_directory(self, executable):
        return os.path.dirname(executable)

    def cmdline(self, executable, options, task, rlimits):
        options = list(options)
        if "pbva" in options:
            options.remove("pbva")
        elif "bva" in options:
            options.remove("bva")
            executable = executable.replace("starexec_run_pbva", "starexec_run_bva")

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
