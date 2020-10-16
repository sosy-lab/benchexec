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

    REQUIRED_PATHS = ["pinaka-wrapper.sh", "pinaka"]

    def executable(self):
        return util.find_executable("pinaka-wrapper.sh")

    def version(self, executable):
        return self._version_from_tool(executable)

    def name(self):
        return "Pinaka"

    def cmdline(self, executable, options, tasks, propertyfile, rlimits):
        if propertyfile:
            options = options + ["--propertyfile", propertyfile]

        return [executable] + options + tasks

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        status = ""

        if returnsignal == 0 and ((returncode == 0) or (returncode == 10)):
            if "VERIFICATION FAILED (ReachSafety)\n" in output:
                status = result.RESULT_FALSE_REACH
            elif "VERIFICATION FAILED (NoOverflow)\n" in output:
                status = result.RESULT_FALSE_OVERFLOW
            elif "VERIFICATION SUCCESSFUL\n" in output:
                status = result.RESULT_TRUE_PROP
            else:
                status = result.RESULT_UNKNOWN
        else:
            status = result.RESULT_ERROR

        return status
