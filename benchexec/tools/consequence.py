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
    ConSequence
    """

    REQUIRED_PATHS = [
        "bin",
        "check.sh",
        "consequence.pl",
        "deps",
        "jars",
        "setup_consequence.pl",
    ]

    def executable(self):
        return util.find_executable("consequence.pl")

    def name(self):
        return "ConSequence"

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        lines = " ".join(output)
        if "consequence_unsafe" in lines:
            return result.RESULT_FALSE_REACH
        elif "consequence_safe" in lines:
            return result.RESULT_TRUE_PROP
        elif "consequence_unknown" in lines:
            return result.RESULT_UNKNOWN
        else:
            return result.RESULT_ERROR
