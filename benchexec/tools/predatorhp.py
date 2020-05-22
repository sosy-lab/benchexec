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
    Wrapper for a Predator - Hunting Party
    http://www.fit.vutbr.cz/research/groups/verifit/tools/predator-hp/
    """

    REQUIRED_PATHS = ["predator", "predator-bfs", "predator-dfs", "predatorHP.py"]

    def executable(self):
        return util.find_executable("predatorHP.py")

    def name(self):
        return "PredatorHP"

    def version(self, executable):
        return self._version_from_tool(executable, use_stderr=True)

    def cmdline(self, executable, options, tasks, propertyfile=None, rlimits={}):
        spec = ["--propertyfile", propertyfile] if propertyfile is not None else []
        return [executable] + options + spec + tasks

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        output = "\n".join(output)
        status = "UNKNOWN"
        if "UNKNOWN" in output:
            status = result.RESULT_UNKNOWN
        elif "TRUE" in output:
            status = result.RESULT_TRUE_PROP
        elif "FALSE(valid-memtrack)" in output:
            status = result.RESULT_FALSE_MEMTRACK
        elif "FALSE(valid-deref)" in output:
            status = result.RESULT_FALSE_DEREF
        elif "FALSE(valid-free)" in output:
            status = result.RESULT_FALSE_FREE
        elif "FALSE(valid-memcleanup)" in output:
            status = result.RESULT_FALSE_MEMCLEANUP
        elif "FALSE" in output:
            status = result.RESULT_FALSE_REACH
        if status == "UNKNOWN" and isTimeout:
            status = "TIMEOUT"
        return status
