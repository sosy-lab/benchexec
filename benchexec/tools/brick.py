# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.util as util
import benchexec.tools.template
import benchexec.result as result


class Tool(benchexec.tools.template.BaseTool):
    """
    Tool info for BRICK
    https://github.com/brick-tool-dev/brick-tool
    """

    REQUIRED_PATHS = ["bin", "lib"]

    def executable(self):
        return util.find_executable("bin/brick")

    def name(self):
        return "BRICK"

    def cmdline(self, executable, options, tasks, propertyfile, rlimits):
        return [executable] + options + tasks

    def version(self, executable):
        return self._version_from_tool(executable, arg="--version")

    def program_files(self, executable):
        paths = self.REQUIRED_PATHS
        return [executable] + self._program_files_from_executable(
            executable, paths, parent_dir=True
        )

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        status = result.RESULT_ERROR

        for line in output:
            if line == "VERIFICATION SUCCESSFUL\n":
                status = result.RESULT_TRUE_PROP
                break
            elif line == "VERIFICATION FAILED\n":
                status = result.RESULT_FALSE_REACH
                break
            elif (
                line == "VERIFICATION UNKNOWN\n"
                or line == "VERIFICATION BOUNDED TRUE\n"
            ):
                status = result.RESULT_UNKNOWN
                break

        return status
