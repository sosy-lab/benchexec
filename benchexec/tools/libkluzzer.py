# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.util as util
import benchexec.tools.template


class Tool(benchexec.tools.template.BaseTool):
    """
    Tool info for LibKluzzer (http://unihb.eu/kluzzer).
    """

    REQUIRED_PATHS = ["bin", "lib", "kluzzer"]

    def program_files(self, executable):
        return self._program_files_from_executable(
            executable, self.REQUIRED_PATHS, parent_dir=True
        )

    def executable(self):
        return util.find_executable("LibKluzzer", "bin/LibKluzzer")

    def version(self, executable):
        return self._version_from_tool(executable)

    def name(self):
        return "LibKluzzer"
