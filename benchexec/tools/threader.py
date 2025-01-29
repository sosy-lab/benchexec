# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import os
import benchexec.util as util
import benchexec.tools.template
import benchexec.result as result


class Tool(benchexec.tools.template.BaseTool):
    """
    This class serves as tool adaptor for Threader
    """

    def executable(self):
        return util.find_executable("threader.sh")

    def program_files(self, executable):
        executableDir = os.path.dirname(executable)
        return [executableDir]

    def working_directory(self, executable):
        executableDir = os.path.dirname(executable)
        return executableDir

    def version(self, executable):
        return self._version_from_tool("cream", "--help").splitlines()[2][34:42]

    def name(self):
        return "Threader"

    def project_url(self):
        return "http://www.esbmc.org/"

    def cmdline(self, executable, options, tasks, propertyfile, rlimits):
        assert len(tasks) == 1, "only one inputfile supported"
        inputfile = tasks[0]
        return [executable] + options + [inputfile]

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        output = "\n".join(output)
        if "SSSAFE" in output:
            status = result.RESULT_TRUE_PROP
        elif "UNSAFE" in output:
            status = result.RESULT_FALSE_REACH
        else:
            status = result.RESULT_UNKNOWN

        if status == result.RESULT_UNKNOWN and isTimeout:
            status = result.RESULT_TIMEOUT

        return status
