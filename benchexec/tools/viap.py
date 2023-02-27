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
    REQUIRED_PATHS = [
        "viap_tool.py",
        "viap_svcomp.py",
        "config.properties",
        "SyntaxFilter.py",
        "graphclass.py",
        "commandclass.py",
        "packages",
    ]

    def executable(self):
        return util.find_executable("viap_tool.py")

    def version(self, executable):
        stdout = self._version_from_tool(executable, "-version")
        return stdout

    def name(self):
        return "VerifierIntegerAssignmentPrograms"

    def cmdline(self, executable, options, tasks, propertyfile, rlimits):
        assert len(tasks) == 1
        assert propertyfile is not None
        spec = ["--spec=" + propertyfile]
        return [executable] + options + spec + tasks

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        status = result.RESULT_UNKNOWN
        stroutput = str(output)
        if "VIAP_STANDARD_OUTPUT_True" in stroutput:
            status = result.RESULT_TRUE_PROP
        elif "VIAP_STANDARD_OUTPUT_False" in stroutput:
            status = result.RESULT_FALSE_REACH
        return status
