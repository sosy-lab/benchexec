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

class Tool(benchexec.tools.template.BaseTool):
    """
    This tool is an trivial tool that calculates pi up to a certain number of digits using bc.
    Use this for example for testing and creating some CPU load.
    """
    def executable(self):
        return util.find_executable('bc')

    def name(self):
        return 'CalculatePI'

    def cmdline(self, executable, options, tasks, propertyfile, rlimits):
        assert len(tasks) == 1
        digits = tasks[0].strip()
        assert int(digits) >= 0
        return ['/bin/sh', '-c',
                'echo "scale={digits}; a(1)*4" | {executable} -l'
                    .format(digits=digits, executable=executable)
                ]
