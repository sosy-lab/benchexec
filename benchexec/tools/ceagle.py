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
    REQUIRED_PATHS = ["sv-ceagle", "z3"]

    def executable(self):
        return util.find_executable("sv-ceagle")

    def version(self, executable):
        return self._version_from_tool(executable)

    def name(self):
        return "Ceagle"

    def cmdline(self, executable, options, tasks, propertyfile, rlimits):
        spec = ["--property-file=" + propertyfile] if propertyfile is not None else []
        return [executable] + options + spec + tasks

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        stroutput = str(output)

        if isTimeout:
            status = result.RESULT_TIMEOUT
        elif "TRUE" in stroutput:
            status = result.RESULT_TRUE_PROP
        elif "FALSE(valid-deref)" in stroutput:
            status = result.RESULT_FALSE_DEREF
        elif "FALSE(no-overflow)" in stroutput:
            status = result.RESULT_FALSE_OVERFLOW
        elif "FALSE" in stroutput:
            status = result.RESULT_FALSE_REACH
        elif "UNKNOWN" in stroutput:
            status = result.RESULT_UNKNOWN
        else:
            status = result.RESULT_UNKNOWN

        return status
