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
import benchexec.tools.template
import benchexec.util as util
import benchexec.result as result

import os

class Tool(benchexec.tools.template.BaseTool):
    """
    Tool wrapper for the Vienna Verification Toolkit
    """

    REQUIRED_PATHS = [
                  "bin",
                  "clang",
                  "include"
                  ]

    def executable(self):
        return util.find_executable('vvt-svcomp-bench.sh', os.path.join("bin", 'vvt-svcomp-bench.sh'))

    def program_files(self, executable):
        installDir = os.path.join(os.path.dirname(executable), os.path.pardir)
        return util.flatten(util.expand_filename_pattern(path, installDir) for path in self.REQUIRED_PATHS)

    def version(self,executable):
        return 'prerelease'

    def name(self):
        return 'VVT'

    def cmdline(self, executable, options, tasks, propertyfile, rlimits):
        return [executable] + tasks

    def determine_result(self, returncode, returnsignal, output, isTimeOut):
        try:
            if "No bug found.\n" in output:
                return result.RESULT_TRUE_PROP
            elif "Bug found:\n" in output:
                return result.RESULT_FALSE_REACH
            else:
                return result.RESULT_UNKNOWN
        except Exception:
            return result.RESULT_UNKNOWN
