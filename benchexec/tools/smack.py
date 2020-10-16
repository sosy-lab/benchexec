# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.result as result
import benchexec.util as util
import benchexec.tools.template

import re


class Tool(benchexec.tools.template.BaseTool):

    REQUIRED_PATHS = ["boogie", "corral", "llvm", "lockpwn", "smack", "smack.sh"]

    def executable(self):
        """
        Tells BenchExec to search for 'smack.sh' as the main executable to be
        called when running SMACK.
        """
        return util.find_executable("smack.sh")

    def version(self, executable):
        """
        Sets the version number for SMACK, which gets displayed in the "Tool" row
        in BenchExec table headers.
        """
        return self._version_from_tool(executable, use_stderr=True).split(" ")[2]

    def name(self):
        """
        Sets the name for SMACK, which gets displayed in the "Tool" row in
        BenchExec table headers.
        """
        return "SMACK"

    def cmdline(self, executable, options, tasks, propertyfile=None, rlimits={}):
        """
        Allows us to define special actions to be taken or command line argument
        modifications to make just before calling SMACK.
        """
        assert len(tasks) == 1
        assert propertyfile is not None
        prop = ["--svcomp-property", propertyfile]
        return [executable] + options + prop + tasks

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        """
        Returns a BenchExec result status based on the output of SMACK
        """
        splitout = "\n".join(output)
        if "SMACK found no errors" in splitout:
            return result.RESULT_TRUE_PROP
        errmsg = re.search(r"SMACK found an error(:\s+([^\.]+))?\.", splitout)
        if errmsg:
            errtype = errmsg.group(2)
            if errtype:
                if "invalid pointer dereference" == errtype:
                    return result.RESULT_FALSE_DEREF
                elif "invalid memory deallocation" == errtype:
                    return result.RESULT_FALSE_FREE
                elif "memory leak" == errtype:
                    return result.RESULT_FALSE_MEMTRACK
                elif "memory cleanup" == errtype:
                    return result.RESULT_FALSE_MEMCLEANUP
                elif "integer overflow" == errtype:
                    return result.RESULT_FALSE_OVERFLOW
            else:
                return result.RESULT_FALSE_REACH
        return result.RESULT_UNKNOWN
