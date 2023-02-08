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
        "bin",
        "include",
        "lctdsvcomp",
        "lib",
        "llvm",
        "server.properties",
    ]

    def executable(self):
        return util.find_executable("lctdsvcomp")

    def name(self):
        return "LCTD"

    def cmdline(self, executable, options, tasks, propertyfile, rlimits):
        assert len(tasks) == 1
        assert len(options) == 0
        return [executable] + tasks

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        if "TRUE\n" in output:
            status = result.RESULT_TRUE_PROP
        elif "FALSE\n" in output:
            status = result.RESULT_FALSE_REACH
        else:
            status = result.RESULT_UNKNOWN
        return status
