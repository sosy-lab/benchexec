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
    def executable(self):
        return util.find_executable("acsar")

    def name(self):
        return "Acsar"

    def cmdline(self, executable, options, tasks, propertyfile, rlimits):
        assert len(tasks) == 1, "only one inputfile supported"
        return [executable] + ["--file"] + tasks + options

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        output = "\n".join(output)
        if "syntax error" in output:
            status = "SYNTAX ERROR"

        elif "runtime error" in output:
            status = "RUNTIME ERROR"

        elif "error while loading shared libraries:" in output:
            status = "LIBRARY ERROR"

        elif "can not be used as a root procedure because it is not defined" in output:
            status = "NO MAIN"

        elif "For Error Location <<ERROR_LOCATION>>: I don't Know " in output:
            status = result.RESULT_TIMEOUT

        elif "received signal 6" in output:
            status = "ABORT"

        elif "received signal 11" in output:
            status = "SEGFAULT"

        elif "received signal 15" in output:
            status = "KILLED"

        elif "Error Location <<ERROR_LOCATION>> is not reachable" in output:
            status = result.RESULT_TRUE_PROP

        elif (
            "Error Location <<ERROR_LOCATION>> is reachable via the following path"
            in output
        ):
            status = result.RESULT_FALSE_REACH

        else:
            status = result.RESULT_UNKNOWN

        return status
