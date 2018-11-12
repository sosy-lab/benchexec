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
import benchexec.tools.template
import benchexec.result as result
import benchexec.util as util

class Tool(benchexec.tools.template.BaseTool):
    """
    This tool is an imaginary tool that can be made to output any result.
    It may be useful for debugging.
    To use it specify tool="dummy" in a benchmark-definition file
    and <option>RESULT</option> to set the output to "RESULT".
    It multiple options are given, the result will be randomly chosen between them
    (the tool prints all options to stdout in random order, and determine_result
    picks the first line that looks like a result).
    """

    def executable(self):
        return util.find_executable('shuf')

    def name(self):
        return 'DummyTool'

    def cmdline(self, executable, options, tasks, propertyfile, rlimits):
        return ([executable, '--echo', '--'] +
                options +
                ["Input file: " + f for f in tasks] +
                ["Property file: " + (propertyfile or "None")]
                )

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        for line in output:
            line = line.strip()
            if line in result.RESULT_LIST:
                return line
        return result.RESULT_UNKNOWN
