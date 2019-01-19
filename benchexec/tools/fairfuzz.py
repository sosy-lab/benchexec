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
import benchexec.result as result
import benchexec.util as util
import benchexec.tools.template
import benchexec.model
import os

class Tool(benchexec.tools.template.BaseTool):
    """
    Tool info for FairFuzz (https://https://github.com/carolemieux/afl-rb/tree/testcomp).
    """

    REQUIRED_PATHS = [
        "bin",
        "helper"
    ]

    def executable(self):
        return util.find_executable('bin/fairfuzz-svtestcomp')

    def program_files(self, executable):
        return self._program_files_from_executable(
            executable, self.REQUIRED_PATHS, parent_dir=True)

    def version(self, executable):
        stdout = self._version_from_tool(executable)
        line = next(l for l in stdout.splitlines() if l.startswith('FairFuzz'))
        line = line.rstrip()
        version_number = line.split("Version ")[1]
        return version_number

    def name(self):
        return 'FairFuzz'


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
        for line in output:
            if "All test cases time out or crash, giving up!" in line:
                return "Couldn't run: all seeds time out or crash"
            if "ERROR: couldn't run FairFuzz" in line:
                return "Couldn't run FairFuzz"
            if "CRASHES FOUND" in line:
                return result.RESULT_FALSE_REACH
            if "DONE RUNNING" in line:
                return result.RESULT_DONE
        return result.RESULT_UNKNOWN

