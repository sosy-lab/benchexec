"""
BenchExec is a framework for reliable benchmarking.
This file is part of BenchExec.

Copyright (C) 2007-2019  Dirk Beyer
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
import re
import benchexec.result as result
import benchexec.util as util
import benchexec.tools.template


class Tool(benchexec.tools.template.BaseTool):
    """
    Tool info for TestCov (https://gitlab.com/sosy-lab/software/test-suite-validator).
    """

    REQUIRED_PATHS = ["suite_validation", "lib", "bin"]

    def program_files(self, executable):
        return self._program_files_from_executable(
            executable, self.REQUIRED_PATHS, parent_dir=True
        )

    def executable(self):
        return util.find_executable("testcov", "bin/testcov")

    def cmdline(self, executable, options, tasks, propertyfile=None, rlimits={}):
        cmd = [executable] + options
        if propertyfile:
            cmd += ["--goal", propertyfile]

        return cmd + tasks

    def version(self, executable):
        return self._version_from_tool(executable)

    def name(self):
        return "TestCov"

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        """
        Parse the output of the tool and extract the verification result.
        This method always needs to be overridden.
        If the tool gave a result, this method needs to return one of the
        benchexec.result.RESULT_* strings.
        Otherwise an arbitrary string can be returned that will be shown to the user
        and should give some indication of the failure reason
        (e.g., "CRASH", "OUT_OF_MEMORY", etc.).
        """
        for line in reversed(output):
            if line.startswith("ERROR:"):
                if "timeout" in line.lower():
                    return "TIMEOUT"
                else:
                    return "ERROR ({0})".format(returncode)
            elif line.startswith("Result: FALSE"):
                return result.RESULT_FALSE_REACH
            elif line.startswith("Result: TRUE"):
                return result.RESULT_TRUE_PROP
            elif line.startswith("Result: DONE"):
                return result.RESULT_DONE
            elif line.startswith("Result: ERROR"):
                # matches ERROR and ERROR followed by some reason in parantheses
                # e.g., "ERROR (TRUE)" or "ERROR(TRUE)"
                return re.search(r"ERROR(\s*\(.*\))?", line).group(0)
        return result.RESULT_UNKNOWN

    def get_value_from_output(self, lines, identifier):
        for line in reversed(lines):
            pattern = identifier
            if pattern[-1] != ":":
                pattern += ":"
            match = re.match("^" + pattern + "([^(]*)", line)
            if match and match.group(1):
                return match.group(1).strip()
        return None
