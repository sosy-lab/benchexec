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
    Tool info for JDart modified by TU Dortmund
    (https://github.com/tudo-aqua/jdart).
    """

    REQUIRED_PATHS = [
        "jconstraints-extensions",
        "lib",
        "z3",
        "basic.jpf",
        "jdk8u222-b10",
        "jconstraints-0.9.2-SNAPSHOT.jar",
        "jpf-annotations.jar",
        "jpf-classes.jar",
        "jpf.jar",
        "jpf-jdart-annotations.jar",
        "jpf-jdart-classes.jar",
        "jpf-jdart.jar",
        "RunJPF.jar",
        "version.txt",
        "jdart.sh",
        "run-jdart.sh",
    ]

    def executable(self):
        return util.find_executable("run-jdart.sh")

    def version(self, executable):
        return self._version_from_tool(executable, arg="-v")

    def name(self):
        return "JDart"

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
            if "== ERROR" in line:
                status = result.RESULT_FALSE_PROP
            elif "== OK" in line:
                status = result.RESULT_TRUE_PROP

        return status
