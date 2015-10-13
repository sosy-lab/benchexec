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
        return util.find_executable('feaver_cmd')


    def name(self):
        return 'Feaver'


    def cmdline(self, executable, options, tasks, propertyfile, rlimits):
        assert len(tasks) == 1, "only one inputfile supported"
        inputfile = tasks[0]

        # create tmp-files for feaver, feaver needs special error-labels
        self.prepInputfile = self._prepareInputfile(inputfile)

        return [executable] + ["--file"] + [self.prepInputfile] + options


    def _prepareInputfile(self, inputfile):
        content = open(inputfile, "r").read()
        content = content.replace("goto ERROR;", "assert(0);")
        newFilename = "tmp_benchmark_feaver.c"
        util.write_file(newFilename, content)
        return newFilename


    def determine_result(self, returncode, returnsignal, output, isTimeout):
        output = '\n'.join(output)
        if "collect2: ld returned 1 exit status" in output:
            status = "COMPILE ERROR"

        elif "Error (parse error" in output:
            status = "PARSE ERROR"

        elif "error: (\"model\":" in output:
            status = "MODEL ERROR"

        elif "Error: syntax error" in output:
            status = "SYNTAX ERROR"

        elif "error: " in output or "Error: " in output:
            status = "ERROR"

        elif "Error Found:" in output:
            status = result.RESULT_FALSE_REACH

        elif "No Errors Found" in output:
            status = result.RESULT_TRUE_PROP

        else:
            status = result.RESULT_UNKNOWN

        # delete tmp-files
        for tmpfile in [self.prepInputfile, self.prepInputfile[0:-1] + "M",
                     "_modex_main.spn", "_modex_.h", "_modex_.cln", "_modex_.drv",
                     "model", "pan.b", "pan.c", "pan.h", "pan.m", "pan.t"]:
            try:
                os.remove(tmpfile)
            except OSError:
                pass

        return status
