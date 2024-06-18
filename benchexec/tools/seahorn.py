# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
# SPDX-FileCopyrightText: 2015 Carnegie Mellon University
#
# SPDX-License-Identifier: LicenseRef-BSD-3-Clause-CMU

# SeaHorn Verification Framework
# DM-0002198

import logging
import os
import benchexec.tools.template
import benchexec.result as result


class Tool(benchexec.tools.template.BaseTool2):
    REQUIRED_PATHS = ["bin", "include", "lib", "share"]

    def executable(self, tool_locator):
        self.use_svcomp_wrapper = False
        try:
            # try to find the SV-COMP wrapper script
            ret = tool_locator.find_executable("sea_svcomp", subdir="bin")
            self.use_svcomp_wrapper = True
            logging.debug("Using SeaHorn's SV-COMP wrapper")
            return ret
        except benchexec.tools.template.ToolNotFoundException:
            # find the default wrapper script
            return tool_locator.find_executable("sea", subdir="bin")

    def program_files(self, executable):
        return self._program_files_from_executable(
            executable, self.REQUIRED_PATHS, parent_dir=True
        )

    def name(self):
        return "SeaHorn"

    def project_url(self):
        return "https://github.com/seahorn/seahorn"

    def cmdline(self, executable, options, task, rlimits):
        if self.use_svcomp_wrapper and task.property_file:
            options += [f"--spec={task.property_file}"]
        return [executable] + options + [task.single_input_file]

    def version(self, executable):
        seahorn_exe = os.path.join(os.path.dirname(executable), "seahorn")
        return self._version_from_tool(seahorn_exe, line_prefix="  SeaHorn version")

    def determine_result(self, run):
        if self.use_svcomp_wrapper:
            if run.output.any_line_contains("BRUNCH_STAT Result TRUE"):
                return result.RESULT_TRUE_PROP
            elif run.output.any_line_contains("BRUNCH_STAT Result FALSE"):
                if run.output.any_line_contains("BRUNCH_STAT Termination"):
                    return result.RESULT_FALSE_TERMINATION
                else:
                    return result.RESULT_FALSE_REACH
            elif run.exit_code.signal == 9 or run.exit_code.signal == (128 + 9):
                if run.was_timeout:
                    return result.RESULT_TIMEOUT
                else:
                    return "KILLED BY SIGNAL 9"
            elif run.exit_code.value != 0:
                return f"ERROR ({run.exit_code.value})"
            else:
                return "FAILURE"
        else:
            if run.output[-1].startswith("sat"):
                return result.RESULT_FALSE_PROP
            if run.output[-1].startswith("unsat"):
                return result.RESULT_TRUE_PROP
            return result.RESULT_ERROR
