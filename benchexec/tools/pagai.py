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
    Wrapper for a PAGAI tool.
    """

    def executable(self):
        return util.find_executable("pagai")

    def name(self):
        return "PAGAI"

    def project_url(self):
        return "http://pagai.forge.imag.fr/"

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        output = "\n".join(output)
        if ((returnsignal == 9) or (returnsignal == 15)) and isTimeout:
            status = result.RESULT_TIMEOUT
        elif returnsignal == 9:
            status = "KILLED BY SIGNAL 9"
        elif "RESULT: TRUE" in output:
            status = result.RESULT_TRUE_PROP
        elif returncode != 0:
            status = f"ERROR ({returncode})"
        elif "RESULT: UNKNOWN" in output:
            status = result.RESULT_UNKNOWN
        else:
            status = result.RESULT_UNKNOWN
        return status
