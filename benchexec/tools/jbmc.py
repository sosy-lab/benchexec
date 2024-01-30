# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.result as result

from . import cbmc


class Tool(cbmc.Tool):
    """
    Tool info for JBMC.
    It always adds --xml-ui to the command-line arguments for easier parsing of
    the output, unless a propertyfile is passed -- in which case running under
    SV-COMP conditions is assumed.
    """

    def executable(self, tool_locator):
        return tool_locator.find_executable("jbmc")

    def name(self):
        return "JBMC"

    def determine_result(self, run):
        status = result.RESULT_ERROR
        if run.exit_code.value in [0, 10]:
            result_str = run.output[-1].strip()

            if result_str == "TRUE":
                status = result.RESULT_TRUE_PROP
            elif result_str == "FALSE":
                status = result.RESULT_FALSE_PROP
            elif "UNKNOWN" in run.output:
                status = result.RESULT_UNKNOWN

        elif run.exit_code.value == 64 and "Usage error!" in run.output:
            status = "INVALID ARGUMENTS"

        elif run.exit_code.value == 6 and "Out of memory" in run.output:
            status = "OUT OF MEMORY"

        return status
