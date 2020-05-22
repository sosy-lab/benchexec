# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.result as result
import benchexec.util as util

from . import cbmc


class Tool(cbmc.Tool):
    """
    Tool info for JBMC (http://www.cprover.org/cbmc/).
    It always adds --xml-ui to the command-line arguments for easier parsing of
    the output, unless a propertyfile is passed -- in which case running under
    SV-COMP conditions is assumed.
    """

    REQUIRED_PATHS = ["jbmc", "jbmc-binary", "core-models.jar"]

    def executable(self):
        return util.find_executable("jbmc")

    def name(self):
        return "JBMC"

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        status = result.RESULT_ERROR
        if returnsignal == 0 and ((returncode == 0) or (returncode == 10)) and output:
            result_str = output[-1].strip()

            if result_str == "TRUE":
                status = result.RESULT_TRUE_PROP
            elif result_str == "FALSE":
                status = result.RESULT_FALSE_PROP
            elif "UNKNOWN\n" in output:
                status = result.RESULT_UNKNOWN

        elif returncode == 64 and "Usage error!\n" in output:
            status = "INVALID ARGUMENTS"

        elif returncode == 6 and "Out of memory\n" in output:
            status = "OUT OF MEMORY"

        return status
