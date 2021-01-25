# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.util as util
import benchexec.tools.template
import benchexec.result as result


class Tool(benchexec.tools.template.BaseTool):
    
    def executable(self):
        #return "~/nanomsg_test/nn_test.py"
        
        return "/home/sdn/Scripts/SocketTest.sh"
        
        #return "/root/Script2"

        #util.find_executable("Script")

    def name(self):
        return "SocketTest1"

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        returnString = "-----This is the output-----\n \n"
        for line in output:
            returnString += line
            #if line == "Success\n":
            #    return result.RESULT_TRUE_PROP
            #else:
            #    return result.RESULT_FALSE_PROP
        return returnString