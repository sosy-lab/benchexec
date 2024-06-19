# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.tools.cpachecker as cpachecker

from benchexec.tools.template import ToolNotFoundException


class Tool(cpachecker.Tool):
    """
    Tool info for CPA-witness2test.
    """

    def executable(self, tool_locator):
        # Makes sure that CPAchecker can be called, shows a warning otherwise
        super(Tool, self).executable(tool_locator)
        # The following will perform these lookups (if --tool-directory is not given)
        # and pick the first one that is found:
        # 1. cpa-witness2test in PATH
        # 2. cpa-witness2test in ./ and bin/
        # 3. cpa_witness2test.py in PATH
        # 4. cpa_witness2test.py in ./ and scripts/
        # This follows the BenchExec logic of "look up first in PATH, then ./"
        # except for the case "cpa_witness2test.py in PATH and cpa-witness2test in bin/",
        # which should be ok.
        try:
            return tool_locator.find_executable("cpa-witness2test", subdir="bin")
        except ToolNotFoundException as e1:
            try:
                return tool_locator.find_executable(
                    "cpa_witness2test.py", subdir="scripts"
                )
            except ToolNotFoundException:
                raise e1

    def version(self, executable):
        stdout = self._version_from_tool(executable, "-version")
        version = stdout.split("(")[0].strip()
        return version

    def name(self):
        return "CPA-witness2test"

    def program_files(self, executable):
        return [executable] + super().program_files(executable)

    def cmdline(self, executable, options, task, rlimits):
        additional_options = self._get_additional_options(options, task, rlimits)
        # Add additional options in front of existing ones, since -gcc-args ... must be last argument in front of task
        return [executable] + additional_options + options + [task.single_input_file]
