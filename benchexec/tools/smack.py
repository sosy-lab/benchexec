# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.result as result
import benchexec.tools.template
from benchexec.tools.template import UnsupportedFeatureException
from benchexec.tools.sv_benchmarks_util import get_data_model_from_task, ILP32, LP64

import re


class Tool(benchexec.tools.template.BaseTool2):

    REQUIRED_PATHS = [
        "bin",
        "lib",
        "share",
        "smack-deps",
        "smack.sh",
        "boogie",
        "corral",
        "llvm",
        "lockpwn",
        "smack",
    ]

    def executable(self, tool_locator):
        """
        Tells BenchExec to search for 'smack.sh' as the main executable to be
        called when running SMACK.
        """
        return tool_locator.find_executable("smack.sh")

    def version(self, executable):
        """
        Sets the version number for SMACK, which gets displayed in the "Tool" row
        in BenchExec table headers.
        """
        smack_output = self._version_from_tool(executable)
        if smack_output:
            return smack_output.split(" ")[2]
        else:
            # old versions of SMACK used to print to stderr
            return self._version_from_tool(executable, use_stderr=True).split(" ")[2]

    def name(self):
        """
        Sets the name for SMACK, which gets displayed in the "Tool" row in
        BenchExec table headers.
        """
        return "SMACK"

    def cmdline(self, executable, options, task, rlimits):
        """
        Allows us to define special actions to be taken or command line argument
        modifications to make just before calling SMACK.
        """
        data_model_param = get_data_model_from_task(task, {ILP32: "-m32", LP64: "-m64"})
        if data_model_param and "--data-model" not in options:
            options += ["--clang-options=" + data_model_param]

        if task.property_file:
            options += ["--svcomp-property", task.property_file]
        else:
            raise UnsupportedFeatureException(
                "SMACK can't execute without a property file."
            )

        options += [task.single_input_file]

        return [executable] + options

    def determine_result(self, run):
        """
        Returns a BenchExec result status based on the output of SMACK
        """
        splitout = "\n".join(run.output)
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
