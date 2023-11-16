# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
# SPDX-FileCopyrightText: 2015 New York University
#
# SPDX-License-Identifier: Apache-2.0

# Cascade Verification Tool

import benchexec.util as util
import benchexec.tools.template
import benchexec.result as result


class Tool(benchexec.tools.template.BaseTool):
    """
    Tool info for Cascade.
    """

    REQUIRED_PATHS = ["bin", "cascade.sh", "lib", "run_cascade"]

    def executable(self):
        return util.find_executable("run_cascade")

    def name(self):
        return "Cascade"

    def project_url(self):
        return "http://cascade.cims.nyu.edu/"

    def version(self, executable):
        return self._version_from_tool(executable)

    def cmdline(self, executable, options, tasks, propertyfile, rlimits):
        assert len(tasks) == 1, "only one sourcefile supported"
        inputfile = tasks[0]
        assert propertyfile is not None
        spec = ["-spec", propertyfile]
        return [executable] + options + spec + [inputfile]

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        output = "\n".join(output)
        if "FALSE" in output:
            if "FALSE(valid-deref)" in output:
                status = result.RESULT_FALSE_DEREF
            elif "FALSE(valid-free)" in output:
                status = result.RESULT_FALSE_FREE
            elif "FALSE(valid-memtrack)" in output:
                status = result.RESULT_FALSE_MEMTRACK
            else:
                status = result.RESULT_FALSE_REACH
        elif "TRUE" in output:
            status = result.RESULT_TRUE_PROP
        else:
            status = result.RESULT_UNKNOWN

        return status
