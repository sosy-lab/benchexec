"""
BenchExec is a framework for reliable benchmarking.
This file is part of BenchExec.

Copyright (C) 2019  Dirk Beyer
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

# prepare for Python 3
from __future__ import absolute_import, division, print_function, unicode_literals

import subprocess
import benchexec.util as util
import benchexec.tools.template

class Tool(benchexec.tools.template.BaseTool):
    """
    Tool info for Frama-C.
    URL: https://frama-c.com/
    """

    REQUIRED_PATHS = [
        "bin",
        "lib",
        "share",
        ]

    def executable(self):
        return util.find_executable('frama-c', 'bin/frama-c')

    def program_files(self, executable):
        return self._program_files_from_executable(executable, self.REQUIRED_PATHS, parent_dir=True)

    def version(self, executable):
        return self._version_from_tool(executable)

    def name(self):
        return 'Frama-C'

    def cmdline(self, executable, options, tasks, propertyfile=None, rlimits={}):
        # Always put task input files before first occurrence of '-then*' parameters
        # This will give task files to the first batch of operations,
        # and execute succeeding batches on the resulting frama-c 'projects'
        try:
            first_then = next(i for i, v in enumerate(options) if v.startswith('-then'))
            return [executable] + options[:first_then] + tasks + options[first_then:]
        except StopIteration:
            return [executable] + options + tasks
