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
from random import random
import benchexec.tools.template
import benchexec.result as result

class Tool(benchexec.tools.template.BaseTool):
    """
    This tool is an imaginary tool that randomly returns SAFE and UNSAFE.
    To use it you need a normal benchmark-xml-file
    with the tool and tasks, however options are ignored.
    """

    def executable(self):
        return '/bin/true'

    def name(self):
        return 'Random'

    def cmdline(self, executable, options, tasks, propertyfile, rlimits):
        return [executable] + tasks

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        return result.RESULT_TRUE_PROP if random() < 0.5 else result.RESULT_FALSE_REACH