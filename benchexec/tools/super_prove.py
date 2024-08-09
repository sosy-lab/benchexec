# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.result as result
import benchexec.tools.template
from pathlib import Path


class Tool(benchexec.tools.template.BaseTool2):
    """
    Tool info for super_prove: A portfolio model checker based on ABC
    - project URL: https://github.com/berkeley-abc/super_prove
    - build repository: https://github.com/sterin/super-prove-build
    """

    REQUIRED_PATHS = ["bin/", "lib/"]

    def executable(self, tool_locator):
        return tool_locator.find_executable("super_prove.sh", subdir="bin")

    def name(self):
        return "super_prove"

    def project_url(self):
        return "https://github.com/berkeley-abc/super_prove"

    def version(self, executable):
        version_file = Path(executable).parent.parent / "VERSION.txt"
        if not version_file.is_file():
            return ""
        with version_file.open() as f:
            version = f.readline().strip()
        return version

    def program_files(self, executable):
        return self._program_files_from_executable(
            executable, self.REQUIRED_PATHS, parent_dir=True
        )

    def cmdline(self, executable, options, task, rlimits):
        return [executable, *options, task.single_input_file]

    def determine_result(self, run):
        """
        @return: status of super_prove after executing a run
        """
        if run.output:
            if run.output[0] == "0":
                return result.RESULT_TRUE_PROP
            elif run.output[0] == "1":
                return result.RESULT_FALSE_PROP
        return result.RESULT_UNKNOWN
