# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.tools.cpachecker as cpachecker


class Tool(cpachecker.Tool):
    """
    Tool info for PIChecker.
    """

    REQUIRED_PATHS = list(cpachecker.Tool.REQUIRED_PATHS) + ["resources"]

    def project_url(self):
        return "https://gitlab.com/Lapulatos/pichecker"

    def version(self, executable):
        version = self._version_from_tool(executable, "-help", line_prefix="PIChecker")
        return version.split("(")[0].strip()

    def name(self):
        return "PIChecker"
