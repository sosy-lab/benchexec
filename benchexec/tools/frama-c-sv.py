# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.util as util
import benchexec.tools.template


class Tool(benchexec.tools.template.BaseTool2):
    """
    Tool info for Frama-C with a wrapper for usage in the SVCOMP.
    URL: https://gitlab.com/sosy-lab/software/frama-c-sv
    """

    REQUIRED_PATHS = ["."]
    _TOOL_NAME = "frama-c-sv"
    _SCRIPT_NAME = _TOOL_NAME + ".py"

    def executable(self, _):
        return util.find_executable(_SCRIPT_NAME)

    def program_files(self, executable):
        return self._program_files_from_executable(
            executable, self.REQUIRED_PATHS, parent_dir=True
        )

    def version(self, executable):
        return self._version_from_tool(executable)

    def name(self):
        return _TOOL_NAME

    def cmdline(self, executable, options, task, rlimits):
        cmd = [_SCRIPT_NAME, "--program"] + list(task.input_files_or_identifier)
        if task.property_file:
            cmd += ["--property", task.property_file]
        return cmd

    def determine_result(self, run):
        return run.output[-1].split(":", maxsplit=2)[-1]
