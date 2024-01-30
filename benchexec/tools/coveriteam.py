# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.tools.template


class Tool(benchexec.tools.template.BaseTool2):
    """
    Tool info for CoVeriTeam: On-Demand Composition of Cooperative Verification Systems.

    This class has 2 purposes:
        1. to serve as an abstract class for specific coveriteam programs like verifiers, validators, etc.
        2. to serve as the tool info module for any generic coveriteam program.
    """

    REQUIRED_PATHS = [
        "coveriteam",
        "bin",
        "lib",
    ]

    def name(self):
        return "CoVeriTeam"

    def project_url(self):
        return "https://gitlab.com/sosy-lab/software/coveriteam"

    def executable(self, tool_locator):
        return tool_locator.find_executable("coveriteam", subdir="bin")

    def version(self, executable):
        return self._version_from_tool(executable)

    def program_files(self, executable):
        return self._program_files_from_executable(
            executable, self.REQUIRED_PATHS, parent_dir=True
        )
