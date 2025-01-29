# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.tools.template
import benchexec.util as util


class Tool(benchexec.tools.template.BaseTool):
    """This calls javac and checks that a task consisting of Java files compiles."""

    def executable(self):
        return util.find_executable("javac")

    def name(self):
        return "javac"

    def version(self, executable):
        return self._version_from_tool(
            executable, arg="-version", use_stderr=True
        ).replace("javac ", "")

    def cmdline(self, executable, options, tasks, propertyfile, rlimits):
        return (
            [executable]
            + options
            + [file for file in util.get_files(tasks) if file.endswith(".java")]
        )
