# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.tools.template
import benchexec.result as result


class Tool(benchexec.tools.template.BaseTool2):
    """
    VeriAbs
    """

    REQUIRED_PATHS = [
        "bin",
        "cpact",
        "jars",
        "exp-in",
        "prism",
        "lib",
        "afl-2.35b",
        "verifuzz",
        "afl-2.35b_v1",
        "frama-c-Chlorine-20180502",
        "UAutomizer-linux",
        "scripts",
        "supportFiles",
    ]

    def executable(self, tool_locator):
        return tool_locator.find_executable("veriabs", subdir="scripts")

    def version(self, executable):
        return self._version_from_tool(executable)

    def program_files(self, executable):
        return self._program_files_from_executable(
            executable, self.REQUIRED_PATHS, parent_dir=True
        )

    def name(self):
        return "VeriAbs"

    def cmdline(self, executable, options, task, rlimits):
        if task.property_file:
            options += ["--property-file", task.property_file]
        return [executable] + options + [task.single_input_file]

    def determine_result(self, run):
        for line in run.output:
            if "VERIABS_VERIFICATION_SUCCESSFUL" in line:
                return result.RESULT_TRUE_PROP
            elif "VERIABS_VERIFICATION_FAILED" in line:
                return result.RESULT_FALSE_REACH
            elif "NOT SUPPORTED" in line or "VERIABS_UNKNOWN" in line:
                return result.RESULT_UNKNOWN

        return result.RESULT_ERROR
