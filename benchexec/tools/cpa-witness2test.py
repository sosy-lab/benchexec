"""
BenchExec is a framework for reliable benchmarking.
This file is part of BenchExec.

Copyright (C) 2007-2017  Dirk Beyer
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

import benchexec.tools.cpachecker as cpachecker
import benchexec.util as util


class Tool(cpachecker.Tool):
    """
    Tool info for CPA-witness2test.
    """

    def executable(self):
        # Makes sure that CPAchecker can be called, shows a warning otherwise
        super(Tool, self).executable()
        return util.find_executable(
            "cpa_witness2test.py", "scripts/cpa_witness2test.py"
        )

    def version(self, executable):
        stdout = self._version_from_tool(executable, "-version")
        version = stdout.split("(")[0].strip()
        return version

    def name(self):
        return "CPA-witness2test"

    def cmdline(self, executable, options, tasks, propertyfile=None, rlimits={}):
        additional_options = self._get_additional_options(
            options, propertyfile, rlimits
        )
        # Add additional options in front of existing ones, since -gcc-args ... must be last argument in front of task
        return [executable] + additional_options + options + tasks
