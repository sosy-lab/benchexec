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
    This class serves as tool adaptor for LLBMC
    """

    def executable(self):
        return util.find_executable("llbmc")

    def version(self, executable):
        return self._version_from_tool(executable).splitlines()[2][8:18]

    def name(self):
        return "LLBMC"

    def cmdline(self, executable, options, tasks, propertyfile, rlimits):
        assert len(tasks) == 1, "only one inputfile supported"
        return [executable] + options + tasks

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        status = result.RESULT_UNKNOWN

        for line in output:
            if "Error detected." in line:
                status = result.RESULT_FALSE_REACH
            elif "No error detected." in line:
                status = result.RESULT_TRUE_PROP

        return status
