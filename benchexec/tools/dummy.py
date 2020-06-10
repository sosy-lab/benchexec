# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.tools.template
import benchexec.result as result
import benchexec.util as util


class Tool(benchexec.tools.template.BaseTool):
    """
    This tool is an imaginary tool that can be made to output any result.
    It may be useful for debugging.
    To use it specify tool="dummy" in a benchmark-definition file
    and <option>RESULT</option> to set the output to "RESULT".
    It multiple options are given, the result will be randomly chosen between them
    (the tool prints all options to stdout in random order, and determine_result
    picks the first line that looks like a result).
    """

    def executable(self):
        return util.find_executable("shuf")

    def name(self):
        return "DummyTool"

    def cmdline(self, executable, options, tasks, propertyfile, rlimits):
        return (
            [executable, "--echo", "--"]
            + options
            + ["Input file: " + f for f in tasks]
            + ["Property file: " + (propertyfile or "None")]
        )

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        for line in output:
            line = line.strip()
            if result.get_result_classification(line) != result.RESULT_CLASS_OTHER:
                return line
        return result.RESULT_UNKNOWN
