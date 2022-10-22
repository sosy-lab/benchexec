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
    Tool info for MLB
    (https://github.com/MLB-SE/Experiment).
    """

    def executable(self):
        return util.find_executable("run.sh")

    def version(self, executable):
        return self._version_from_tool(executable, arg="-version")

    def name(self):
        return "MLB"

    def cmdline(self, executable, options, tasks, propertyfile, rlimits):
        cmd = [executable]
        if options:
            cmd = cmd + options
        if propertyfile:
            cmd.append(propertyfile)
        return cmd + tasks

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        # parse output
        status = result.RESULT_UNKNOWN
        for line in output:
            if "==> FALSE" in line:
                status = result.RESULT_FALSE_PROP
            elif "==> TRUE" in line:
                status = result.RESULT_TRUE_PROP

        return status
