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
    def executable(self):
        return util.find_executable("yogar-cbmc")

    def name(self):
        return "Yogar-CBMC"

    def version(self, executable):
        return self._version_from_tool(executable)

    def cmdline(self, executable, options, tasks, propertyfile, rlimits):
        options = options + ["--no-unwinding-assertions"]
        return [executable] + options + tasks

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        status = result.RESULT_UNKNOWN
        stroutput = str(output)

        if isTimeout:
            status = result.RESULT_TIMEOUT
        elif "SUCCESSFUL" in stroutput:
            status = result.RESULT_TRUE_PROP
        elif "FAILED" in stroutput:
            status = result.RESULT_FALSE_REACH
        elif "UNKNOWN" in stroutput:
            status = result.RESULT_UNKNOWN
        else:
            status = result.RESULT_UNKNOWN

        return status
