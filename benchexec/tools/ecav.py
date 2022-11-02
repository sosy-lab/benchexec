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
        return util.find_executable("ecaverifier")

    def name(self):
        return "EcaVerifier"

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        status = result.RESULT_UNKNOWN
        for line in output:
            if line.startswith("0 safe, 1 unsafe"):
                status = result.RESULT_FALSE_REACH
            elif line.startswith("1 safe, 0 unsafe"):
                status = result.RESULT_TRUE_PROP
            elif ((returnsignal == 9) or (returnsignal == 15)) and isTimeout:
                status = result.RESULT_TIMEOUT
            elif returnsignal == 9:
                status = "KILLED BY SIGNAL 9"

        return status
