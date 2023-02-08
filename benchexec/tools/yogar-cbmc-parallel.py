# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.util as util

yogar_cbmc = __import__("benchexec.tools.yogar-cbmc", fromlist=["Tool"])


class Tool(yogar_cbmc.Tool):
    REQUIRED_PATHS = ["yogar-cbmc"]

    def executable(self):
        return util.find_executable("yogar-cbmc-parallel")

    def name(self):
        return "Yogar-CBMC-Parallel"

    def version(self, executable):
        return self._version_from_tool(executable)

    def cmdline(self, executable, options, tasks, propertyfile, rlimits):
        return [executable] + options + tasks
