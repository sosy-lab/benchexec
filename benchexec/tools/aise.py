# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.result as result
import benchexec.tools.template
import benchexec.model
from benchexec.tools.sv_benchmarks_util import get_data_model_from_task, ILP32, LP64


class Tool(benchexec.tools.template.BaseTool2):
    """
    Tool info for AISE.
    """

    def executable(self, tool_locator):
        return tool_locator.find_executable("aise", subdir="bin")

    def cmdline(self, executable, options, task, rlimits):
        data_model_param = get_data_model_from_task(task, {ILP32: "--32", LP64: "--64"})
        if data_model_param and data_model_param not in options:
            options += [data_model_param]
        return [executable] + options + [task.single_input_file]

    def name(self):
        return "AISE"

    def project_url(self):
        return "https://github.com/ZhenWang233/AISE"

    def version(self, executable):
        return self._version_from_tool(executable, arg="--version")

    def determine_result(self, run):
        """
        Parse the output of the tool and extract the verification result.
        This method always needs to be overridden.
        If the tool gave a result, this method needs to return one of the
        benchexec.result.RESULT_* strings.
        Otherwise an arbitrary string can be returned that will be shown to the user
        and should give some indication of the failure reason
        (e.g., "CRASH", "OUT_OF_MEMORY", etc.).
        """
        for line in run.output:
            if line.startswith("KLEE: ERROR: ") and "ASSERTION FAIL:" in line:
                return result.RESULT_FALSE_REACH
        for line in run.output:
            if line.startswith("CLAM ERROR:"):
                return result.RESULT_ERROR
            elif line.startswith("KLEE: WARNING") and "silently concretizing" in line:
                return result.RESULT_UNKNOWN
            elif line.startswith("KLEE: ERROR: "):
                if "memory error: out of bound pointer" in line:
                    return result.RESULT_FALSE_DEREF
                elif "overflow" in line:
                    return result.RESULT_FALSE_OVERFLOW
                elif "abort failure" in line:
                    continue
                elif "concretized symbolic size" in line:
                    return result.RESULT_UNKNOWN
                else:
                    return result.RESULT_ERROR
            elif line.startswith("KLEE: done"):
                if "AISE_VERIFICATION_TRUE" in line:
                    return result.RESULT_TRUE_PROP
                elif "AISE_VERIFICATION_FALSE" in line:
                    return result.RESULT_FALSE_REACH
                elif "AISE_VERIFICATION_UNKNOWN" in line:
                    return result.RESULT_UNKNOWN
                return result.RESULT_DONE
        return result.RESULT_UNKNOWN
