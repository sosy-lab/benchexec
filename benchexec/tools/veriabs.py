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
import os

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
                      "scripts",
                      "supportFiles",
                      ]

    def executable(self):
        return util.find_executable('scripts/veriabs')

    def program_files(self, executable):
        installDir = os.path.join(os.path.dirname(executable), os.path.pardir)
        return util.flatten(util.expand_filename_pattern(path, installDir) for path in self.REQUIRED_PATHS)

    def name(self):
        return 'VeriAbs'

    def cmdline(self, executable, options, tasks, propertyfile, rlimits):
        if propertyfile:
            options = options + ['--property-file', propertyfile]
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
