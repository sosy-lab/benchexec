# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.result as result
import benchexec.util as util
import benchexec.tools.template


class Tool(benchexec.tools.template.BaseTool):
    REQUIRED_PATHS = ["tabol.sh", "tabol.jar", "output/", "tools"]

    def executable(self):
        return util.find_executable("tabol.sh")

    def name(self):
        return "TABOL"

    def cmdline(self, executable, options, tasks, propertyfile, rlimits):
        return [executable] + options + tasks

    def version(self, executable):
        return self._version_from_tool(executable)

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        status = result.RESULT_UNKNOWN

        if isTimeout:
            status = result.RESULT_UNKNOWN
        elif "TABOL_TRUE" in output:
            status = result.RESULT_TRUE_PROP
        elif "TABOL_FALSE" in output:
            status = result.RESULT_FALSE_TERMINATION
        else:
            status = result.RESULT_UNKNOWN

        return status
