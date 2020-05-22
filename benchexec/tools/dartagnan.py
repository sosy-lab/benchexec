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
    Tool info for Dartagnan (https://github.com/hernanponcedeleon/Dat3M).
    """

    REQUIRED_PATHS = [
        "svcomp/target",
        "dartagnan/target",
        "cat",
        "lib",
        "smack",
        "output",
    ]

    def executable(self):
        return util.find_executable("./Dartagnan-SVCOMP.sh")

    def name(self):
        return "Dartagnan"

    def cmdline(self, executable, options, tasks, propertyfile=None, rlimits={}):
        return [executable] + options + tasks

    def version(self, executable):
        return self._version_from_tool(executable)

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        status = result.RESULT_ERROR
        if output:
            result_str = output[-1].strip()
            if "FAIL" in result_str:
                status = result.RESULT_FALSE_REACH
            elif "PASS" in result_str:
                status = result.RESULT_TRUE_PROP
            elif "UNKNOWN" in result_str:
                status = result.RESULT_UNKNOWN
        return status

    def program_files(self, executable):
        return [executable] + self.REQUIRED_PATHS
