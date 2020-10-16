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
    VeriFuzz
    """

    REQUIRED_PATHS = [
        "lib",
        "exp-in",
        "seeds",
        "fuzzEngine",
        "scripts",
        "supportFiles",
        "prism",
        "bin",
        "jars",
    ]

    def executable(self):
        return util.find_executable("scripts/verifuzz.py")

    def version(self, executable):
        return self._version_from_tool(executable, use_stderr=True)

    def program_files(self, executable):
        return self._program_files_from_executable(
            executable, self.REQUIRED_PATHS, parent_dir=True
        )

    def name(self):
        return "VeriFuzz"

    def cmdline(self, executable, options, tasks, propertyfile, rlimits):
        if propertyfile:
            options = options + ["--propertyFile", propertyfile]
        return [executable] + options + tasks

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        lines = " ".join(output)
        if "COVER(error-call)" in lines:
            return result.RESULT_DONE
        elif "COVER(branches)" in lines:
            return result.RESULT_DONE
        elif "VERIFUZZ_VERIFICATION_SUCCESSFUL" in lines:
            return result.RESULT_TRUE_PROP
        elif "VERIFUZZ_VERIFICATION_FAILED" in lines:
            return result.RESULT_FALSE_REACH
        elif "FALSE(unreach-call)" in lines:
            return result.RESULT_FALSE_REACH
        elif "FALSE(no-overflow)" in lines:
            return result.RESULT_FALSE_OVERFLOW
        elif "FALSE(termination)" in lines:
            return result.RESULT_FALSE_TERMINATION
        elif "FALSE(valid-deref)" in lines:
            return result.RESULT_FALSE_DEREF
        elif "FALSE(valid-free)" in lines:
            return result.RESULT_FALSE_FREE
        elif "FALSE(valid-memtrack)" in lines:
            return result.RESULT_FALSE_MEMTRACK
        elif "NOT SUPPORTED" in lines or "VERIFUZZ_UNKNOWN" in lines:
            return result.RESULT_UNKNOWN
        else:
            return result.RESULT_ERROR
