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
    Tool info for GACAL.
    URL: https://gitlab.com/bquiring/sv-comp-submission
    """

    REQUIRED_PATHS = [
        "gacal",
        "gacal.core",
        "parser",
        "run-gacal.py",
        "src",
        "scripts",
    ]

    def executable(self):
        return util.find_executable("run-gacal.py")

    def name(self):
        return "GACAL"

    def version(self, executable):
        return self._version_from_tool(executable)

    def cmdline(self, executable, options, tasks, propertyfile, rlimits):
        return [executable] + options + tasks

    def determine_result(self, returncode, returnsignal, output, is_timeout):
        for line in output:
            if "VERIFICATION_SUCCESSFUL" in line:
                return result.RESULT_TRUE_PROP
            elif "VERIFICATION_FAILED" in line:
                return result.RESULT_FALSE_REACH
            elif "COULD NOT PROVE ALL ASSERTIONS" in line or "UNKNOWN" in line:
                return result.RESULT_UNKNOWN
        return result.RESULT_UNKNOWN
