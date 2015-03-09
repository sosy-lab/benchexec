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

import benchexec.util as util
import benchexec.tools.template
import benchexec.result as result

class Tool(benchexec.tools.template.BaseTool):

    def executable(self):
        return util.find_executable('acsar')


    def name(self):
        return 'Acsar'


    def cmdline(self, executable, options, tasks, propertyfile, rlimits):
        assert len(tasks) == 1, "only one inputfile supported"
        inputfile = tasks[0]

        # create tmp-files for acsar, acsar needs special error-labels
        self.prepInputfile = self._prepareInputfile(inputfile)

        return [executable] + ["--file"] + [self.prepInputfile] + options


    def _prepareInputfile(self, inputfile):
        content = open(inputfile, "r").read()
        content = content.replace(
            "ERROR;", "ERROR_LOCATION;").replace(
            "ERROR:", "ERROR_LOCATION:").replace(
            "errorFn();", "goto ERROR_LOCATION; ERROR_LOCATION:;")
        newFilename = inputfile + "_acsar.c"
        util.write_file(newFilename, content)
        return newFilename


    def determine_result(self, returncode, returnsignal, output, isTimeout):
        output = '\n'.join(output)
        if "syntax error" in output:
            status = "SYNTAX ERROR"

        elif "runtime error" in output:
            status = "RUNTIME ERROR"

        elif "error while loading shared libraries:" in output:
            status = "LIBRARY ERROR"

        elif "can not be used as a root procedure because it is not defined" in output:
            status = "NO MAIN"

        elif "For Error Location <<ERROR_LOCATION>>: I don't Know " in output:
            status = "TIMEOUT"

        elif "received signal 6" in output:
            status = "ABORT"

        elif "received signal 11" in output:
            status = "SEGFAULT"

        elif "received signal 15" in output:
            status = "KILLED"

        elif "Error Location <<ERROR_LOCATION>> is not reachable" in output:
            status = result.RESULT_TRUE_PROP

        elif "Error Location <<ERROR_LOCATION>> is reachable via the following path" in output:
            status = result.RESULT_FALSE_REACH

        else:
            status = result.RESULT_UNKNOWN

        # delete tmp-files
        os.remove(self.prepInputfile)

        return status
