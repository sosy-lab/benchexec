# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
# SPDX-FileCopyrightText: 2015 Matt Roberts
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.util as util
import benchexec.tools.template
import benchexec.result as result


class Tool(benchexec.tools.template.BaseTool):
    REQUIRED_PATHS = [
        "bin",
        "lib",
        "include",
        "logback-test.xml",
        "skink.sh",
        "skink.jar",
        "skink-fpbv.jar",
        "application.conf",
    ]

    def executable(self):
        return util.find_executable("skink.sh")

    def name(self):
        return "skink"

    def version(self, executable):
        return self._version_from_tool(executable)

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        output = "\n".join(output)
        if "TRUE" in output:
            status = result.RESULT_TRUE_PROP
        elif "FALSE" in output:
            status = result.RESULT_FALSE_REACH
        else:
            status = result.RESULT_UNKNOWN
        return status
