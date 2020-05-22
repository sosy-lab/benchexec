# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.util as util
import benchexec.tools.template
import benchexec.result as result


class Tool(benchexec.tools.template.BaseTool):
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

    def executable(self):
        return util.find_executable("scripts/veriabs")

    def version(self, executable):
        return self._version_from_tool(executable)

    def program_files(self, executable):
        return self._program_files_from_executable(
            executable, self.REQUIRED_PATHS, parent_dir=True
        )

    def name(self):
        return "VeriAbs"

    def cmdline(self, executable, options, tasks, propertyfile, rlimits):
        if propertyfile:
            options = options + ["--property-file", propertyfile]
        return [executable] + options + tasks

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        lines = " ".join(output)
        if "VERIABS_VERIFICATION_SUCCESSFUL" in lines:
            return result.RESULT_TRUE_PROP
        elif "VERIABS_VERIFICATION_FAILED" in lines:
            return result.RESULT_FALSE_REACH
        elif "NOT SUPPORTED" in lines or "VERIABS_UNKNOWN" in lines:
            return result.RESULT_UNKNOWN
        else:
            return result.RESULT_ERROR
