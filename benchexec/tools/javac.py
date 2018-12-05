"""
BenchExec is a framework for reliable benchmarking.
This file is part of BenchExec.

Copyright (C) 2007-2018  Dirk Beyer
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
import benchexec.result as result
import benchexec.util as util

class Tool(benchexec.tools.template.BaseTool):
    """This calls javac and checks that a task consisting of Java files compiles."""

    def executable(self):
        return util.find_executable('javac')

    def name(self):
        return 'javac'

    def version(self, executable):
        return (self
            ._version_from_tool(executable, arg="-version", use_stderr=True)
            .replace("javac ", ""))

    def cmdline(self, executable, options, tasks, propertyfile, rlimits):
        return ([executable]
            + options
            + [file for file in util.get_files(tasks) if file.endswith(".java")]
            )
