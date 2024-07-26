# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2024 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import re
from pathlib import Path

from benchexec.tools import template


class Tool(template.BaseTool2):
    """
    This tool-info module runs KeY CLI, a cli version of the KeY deductive verifier.
    """

    REQUIRED_PATHS = ["bin", "lib"]

    def executable(self, tool_locator):
        return tool_locator.find_executable("key-cli", subdir="bin")

    def version(self, executable):
        lib = Path(executable).parent.parent / "lib"
        for file in lib.glob("key-*-exe.jar"):
            match = re.match(r"key-(.*)-exe.jar", file.name)

            if match:
                return match.group(1)

        return ""

    def program_files(self, executable):
        return self._program_files_from_executable(
            executable, self.REQUIRED_PATHS, parent_dir=True
        )

    def name(self):
        return "KeY"

    def project_url(self):
        return "https://www.key-project.org/"

    def cmdline(self, executable, options, task, rlimits):
        return [executable, *options, task.single_input_file]
