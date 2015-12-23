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

import benchexec.result as result
import benchexec.util as util
import benchexec.tools.template

class Tool(benchexec.tools.template.BaseTool):
    """
    Wrapper for PAC-MAN
    """

    REQUIRED_PATHS = [
                  "array",
                  "build.sh",
                  "CPAchecker-1.4-svn",
                  "crest-0.1.2",
                  "genWitness",
                  "ocaml",
                  "pacman.sh",
                  "releases",
                  "scripts",
                  "yices-1.0.40"
                  ]

    def executable(self):
        """
        Find the path to the executable file that will get executed.
        The path returned should be relative to the current directory.
        """
        executable = util.find_executable('pacman.sh')
        return executable


    def name(self):
        """
        Return the name of the tool, formatted for humans.
        """
        return 'PAC-MAN'


    def determine_result(self, returncode, returnsignal, output, isTimeout):
        output = '\n'.join(output)
        status = result.RESULT_UNKNOWN
        if "FALSE" in output:
            status = result.RESULT_FALSE_REACH
        elif "TRUE" in output:
            status = result.RESULT_TRUE_PROP
        return status

