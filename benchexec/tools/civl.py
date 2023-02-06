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
    REQUIRED_PATHS = ["civl", "lib", "provers"]

    def executable(self):
        return util.find_executable("civl")

    def name(self):
        return "CIVL"

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        if any("__VERIFIER_error() is called." in s for s in output):
            status = result.RESULT_FALSE_REACH
        elif any(
            "The standard properties hold for all executions." in s for s in output
        ):
            status = result.RESULT_TRUE_PROP
        else:
            status = result.RESULT_UNKNOWN

        return status
