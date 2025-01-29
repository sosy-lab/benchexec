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
    REQUIRED_PATHS = [
        "fixcalc",
        "hip",
        "hiptnt",
        "hiptnt.sh",
        "oc",
        "prelude.ss",
        "run_hiptnt",
        "stdlib.h",
        "z3-4.3.2",
    ]

    def executable(self):
        return util.find_executable("hiptnt.sh")

    def name(self):
        return "HipTNT+"

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        output = "\n".join(output)
        status = result.RESULT_UNKNOWN
        if "error" in output:
            status = result.RESULT_UNKNOWN
        elif "UNKNOWN" in output:
            status = result.RESULT_UNKNOWN
        elif "TRUE" in output:
            status = result.RESULT_TRUE_PROP
        elif "FALSE" in output:
            status = result.RESULT_FALSE_TERMINATION
        else:
            status = result.RESULT_UNKNOWN
        return status
