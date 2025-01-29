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
        return util.find_executable("feaver_cmd")

    def name(self):
        return "Feaver"

    def cmdline(self, executable, options, tasks, propertyfile, rlimits):
        assert len(tasks) == 1, "only one inputfile supported"
        return [executable] + ["--file"] + tasks + options

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        output = "\n".join(output)
        if "collect2: ld returned 1 exit status" in output:
            status = "COMPILE ERROR"

        elif "Error (parse error" in output:
            status = "PARSE ERROR"

        elif 'error: ("model":' in output:
            status = "MODEL ERROR"

        elif "Error: syntax error" in output:
            status = "SYNTAX ERROR"

        elif "error: " in output or "Error: " in output:
            status = "ERROR"

        elif "Error Found:" in output:
            status = result.RESULT_FALSE_REACH

        elif "No Errors Found" in output:
            status = result.RESULT_TRUE_PROP

        else:
            status = result.RESULT_UNKNOWN

        return status
