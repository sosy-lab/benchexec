# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.tools.template
import benchexec.util as util
import benchexec.result as result

import os


class Tool(benchexec.tools.template.BaseTool):
    """
    Tool wrapper for the Vienna Verification Toolkit
    """

    REQUIRED_PATHS = ["bin", "clang", "include"]

    def executable(self):
        return util.find_executable(
            "vvt-svcomp-bench.sh", os.path.join("bin", "vvt-svcomp-bench.sh")
        )

    def program_files(self, executable):
        return self._program_files_from_executable(
            executable, self.REQUIRED_PATHS, parent_dir=True
        )

    def version(self, executable):
        return "prerelease"

    def name(self):
        return "VVT"

    def cmdline(self, executable, options, tasks, propertyfile, rlimits):
        return [executable] + tasks

    def determine_result(self, returncode, returnsignal, output, isTimeOut):
        try:
            for line in output:
                if line.startswith("No bug found"):
                    return result.RESULT_TRUE_PROP
                elif line.startswith("Bug found:"):
                    return result.RESULT_FALSE_REACH
            return result.RESULT_UNKNOWN
        except Exception:
            return result.RESULT_UNKNOWN
