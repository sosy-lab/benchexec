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
    def executable(self):
        return util.find_executable("wolverine")

    def version(self, executable):
        return self._version_from_tool(executable)[1].strip()

    def name(self):
        return "Wolverine"

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        output = "\n".join(output)
        if "VERIFICATION SUCCESSFUL" in output:
            assert returncode == 0
            status = result.RESULT_TRUE_PROP
        elif "VERIFICATION FAILED" in output:
            assert returncode == 10
            status = result.RESULT_FALSE_REACH
        elif returnsignal == 9:
            status = result.RESULT_TIMEOUT
        elif returnsignal == 6 or (returncode == 6 and "Out of memory" in output):
            status = "OUT OF MEMORY"
        elif returncode == 6 and "PARSING ERROR" in output:
            status = "PARSING ERROR"
        else:
            status = "FAILURE"
        return status
