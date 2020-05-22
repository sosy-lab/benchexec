# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.tools.template
import benchexec.result as result


class Tool(benchexec.tools.template.BaseTool):
    """
    This tool is an imaginary tool that returns always UNSAFE.
    To use it you need a normal benchmark-xml-file
    with the tool and tasks, however options are ignored.
    """

    def executable(self):
        return "/bin/false"

    def name(self):
        return "AlwaysFalseReach"

    def cmdline(self, executable, options, tasks, propertyfile, rlimits):
        return [executable] + tasks

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        return result.RESULT_FALSE_REACH
