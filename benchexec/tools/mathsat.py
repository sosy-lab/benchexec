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

# prepare for Python 3
from __future__ import absolute_import, division, print_function, unicode_literals

import benchexec.util as util
import benchexec.tools.smtlib2

class Tool(benchexec.tools.smtlib2.Smtlib2Tool):
    """
    Tool info for MathSAT.
    """

    def executable(self):
        return util.find_executable('mathsat')

    def version(self, executable):
        line = self._version_from_tool(executable, '-version')
        line = line.replace('MathSAT5 version' , '')
        line = line.split('(')[0]
        return line.strip()

    def name(self):
        return 'MathSAT'

    def cmdline(self, executable, options, tasks, propertyfile=None, rlimits={}):
        assert len(tasks) == 1, "only one inputfile supported"
        return ['/bin/bash', '-c', 'exec ' + executable + " ".join(options) + ' < ' + tasks[0]]