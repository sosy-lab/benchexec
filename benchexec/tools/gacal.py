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

import benchexec.util as util
import benchexec.tools.template
import benchexec.result as result


class Tool(benchexec.tools.template.BaseTool):
    """
    Tool info for GACAL.
    URL: https://gitlab.com/bquiring/sv-comp-submission
    """

    REQUIRED_PATHS = [
        "gacal",
        "gacal.core",
        "parser",
        "run-gacal.py",
        "src",
        "scripts",
    ]

    def executable(self):
        return util.find_executable("run-gacal.py")

    def name(self):
        return "GACAL"

    def version(self, executable):
        return self._version_from_tool(executable)

    def cmdline(self, executable, options, tasks, propertyfile, rlimits):
        return [executable] + options + tasks

    def determine_result(self, returncode, returnsignal, output, is_timeout):
        for line in output:
            if "VERIFICATION_SUCCESSFUL" in line:
                return result.RESULT_TRUE_PROP
            elif "VERIFICATION_FAILED" in line:
                return result.RESULT_FALSE_REACH
            elif "COULD NOT PROVE ALL ASSERTIONS" in line or "UNKNOWN" in line:
                return result.RESULT_UNKNOWN
        return result.RESULT_UNKNOWN
