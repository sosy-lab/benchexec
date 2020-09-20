# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.util as util
import benchexec.tools.template
import benchexec.result as result

import re


class Tool(benchexec.tools.template.BaseTool):
    """
    Tool info for Goblint.
    URL: https://goblint.in.tum.de/
    """

    REQUIRED_PATHS = ["includes/sv-comp.c"]

    def executable(self):
        return util.find_executable("goblint")

    def version(self, executable):
        return self._version_from_tool(executable, line_prefix="Goblint version: ")

    def name(self):
        return "Goblint"

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        for line in output:
            line = line.strip()
            if line == "SV-COMP (unreach-call): true":
                return result.RESULT_TRUE_PROP
            elif line == "SV-COMP (unreach-call): false":
                return result.RESULT_FALSE_REACH
            elif line == "SV-COMP (unreach-call): unknown":
                return result.RESULT_UNKNOWN
            elif "Fixpoint not reached" in line:
                return result.RESULT_ERROR + " (fixpoint)"
            elif "Fatal error" in line:
                if "Assertion failed" in line:
                    return "ASSERTION"
                else:
                    m = re.search(r"Fatal error: exception ([A-Za-z._]+)", line)
                    if m:
                        return "EXCEPTION ({})".format(m.group(1))
                    else:
                        return "EXCEPTION"

        if isTimeout:
            return "TIMEOUT"
        elif returncode != 0:
            return result.RESULT_ERROR
        else:
            return result.RESULT_UNKNOWN
