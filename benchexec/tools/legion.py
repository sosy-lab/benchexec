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


class Tool(benchexec.tools.template.BaseTool):
    """
    Tool info for Legion (https://github.com/Alan32Liu/Principes).
    """

    REQUIRED_PATHS = [
        "legion-sv",
        "Legion.py",
        "__VERIFIER.c",
        "__VERIFIER32.c",
        "__VERIFIER_assume.c",
        "__VERIFIER_assume.instr.s",
        "__trace_jump.s",
        "__trace_buffered.c",
        "tracejump.py",
        "lib",
    ]

    def executable(self):
        return util.find_executable("legion-sv")

    def version(self, executable):
        return self._version_from_tool(executable)

    def name(self):
        return "Legion"
