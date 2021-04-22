# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
# SPDX-FileCopyrightText: 2015 Carnegie Mellon University
#
# SPDX-License-Identifier: LicenseRef-BSD-3-Clause-CMU

# SeaHorn Verification Framework
# DM-0002198

import benchexec.util as util
import benchexec.tools.template
import benchexec.result as result

import os


class Tool(benchexec.tools.template.BaseTool):

    REQUIRED_PATHS = ["bin", "include", "lib", "share"]

    def executable(self):
        return util.find_executable("sea_svcomp", os.path.join("bin", "sea_svcomp"))

    def program_files(self, executable):
        return self._program_files_from_executable(
            executable, self.REQUIRED_PATHS, parent_dir=True
        )

    def name(self):
        return "SeaHorn-F16"

    def cmdline(self, executable, options, tasks, propertyfile, rlimits):
        assert len(tasks) == 1
        assert propertyfile is not None
        spec = ["--spec=" + propertyfile]
        return [executable] + options + spec + tasks

    def version(self, executable):
        return self._version_from_tool(executable)

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        output = "\n".join(output)
        if "BRUNCH_STAT Result TRUE" in output:
            status = result.RESULT_TRUE_PROP
        elif "BRUNCH_STAT Result FALSE" in output:
            if "BRUNCH_STAT Termination" in output:
                status = result.RESULT_FALSE_TERMINATION
            else:
                status = result.RESULT_FALSE_REACH
        elif returnsignal == 9 or returnsignal == (128 + 9):
            if isTimeout:
                status = "TIMEOUT"
            else:
                status = "KILLED BY SIGNAL 9"
        elif returncode != 0:
            status = f"ERROR ({returncode})"
        else:
            status = "FAILURE"

        return status
