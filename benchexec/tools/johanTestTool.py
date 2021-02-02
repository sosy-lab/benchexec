# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.util as util
import benchexec.tools.template
import benchexec.result as result


class Tool(benchexec.tools.template.BaseTool2):
    
    def executable(self, tool):
        #return "~/nanomsg_test/nn_test.py"
        
        return "/home/sdn/Scripts/SocketTest.sh"
        
        #return "/root/Script2"

        #util.find_executable("Script")

    def name(self):
        return "SocketTest1"

    def determine_result(self, run):
        returnString = "-----This is the output-----\n \n"
        for line in run.output:
            if "ok" in line:
                 return benchexec.result.RESULT_CLASS_TRUE
            else:
                return benchexec.result.RESULT_CLASS_FALSE
        return returnString