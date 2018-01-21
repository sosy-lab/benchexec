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
import logging
import xml.etree.ElementTree as ET
import os

import benchexec.util as util
import benchexec.tools.template
import benchexec.result as result

class Tool(benchexec.tools.template.BaseTool):
    """
    Tool info for JPF (https://babelfish.arc.nasa.gov/hg/jpf).
    It creates a temporary .jpf configuration file.
    """

    REQUIRED_PATHS = [
                  "jpf-core/bin/jpf",
                  "jpf-core/build/RunJPF.jar"
                  ]
    def executable(self):
        return util.find_executable('jpf-core/bin/jpf')


    def version(self, executable):
        return self._version_from_tool(executable, '-version').split()[2]


    def name(self):
        return 'JPF'


    def cmdline(self, executable, options, tasks, propertyfile, rlimits):
        # create configuration file
        with open('config.jpf', 'w') as ofile:
            ofile.write(
                'target=Main\n'
                'classpath=' + tasks[0] + '\n'
                'symbolic.dp=z3\n'
                'listener = .symbc.SymbolicListener\n')

        options = options + ['config.jpf']

        self.options = options

        return [executable] + options


    def determine_result(self, returncode, returnsignal, output, isTimeout):
        # clean up
        os.unlink('config.jpf')

        # parse output
        status = result.RESULT_UNKNOWN

        for line in output:
            if 'no errors detected' in line:
                status = result.RESULT_TRUE_PROP
            elif 'AssertionError' in line:
                status = result.RESULT_FALSE_REACH

        return status
