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
        return util.find_executable("ufo.sh")

    def name(self):
        return "Ufo"

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        output = "\n".join(output)
        if returnsignal == 9 or returnsignal == (128 + 9):
            if isTimeout:
                status = result.RESULT_TIMEOUT
            else:
                status = "KILLED BY SIGNAL 9"
        elif returncode == 1 and "program correct: ERROR unreachable" in output:
            status = "SAFE"
        elif returncode != 0:
            status = f"ERROR ({returncode})"
        elif "ERROR reachable" in output:
            status = "UNSAFE"
        elif "program correct: ERROR unreachable" in output:
            status = "SAFE"
        else:
            status = "FAILURE"
        return status
