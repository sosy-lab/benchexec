"""
BenchExec is a framework for reliable benchmarking.
This file is part of BenchExec.

Copyright (C) 2007-2015  Dirk Beyer
All rights reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
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
