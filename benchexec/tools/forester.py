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
    REQUIRED_PATHS = ["include", "libfa.so", "sv_comp_run.py"]

    def executable(self):
        return util.find_executable("sv_comp_run.py")

    def name(self):
        return "Forester"

    def cmdline(self, executable, options, tasks, propertyfile=None, rlimits={}):
        return (
            [executable] + options + ["--properties", propertyfile, "--false"] + tasks
        )

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        # Note, that the order in list matters. FALSE cannot be in
        # front of the other FALSE(<property>)
        possible_outputs = [
            "TRUE",
            "UNKNOWN",
            "FALSE(valid-memtrack)",
            "FALSE(valid-deref)",
            "FALSE(valid-free)",
            "FALSE",
        ]
        results = {
            "TRUE": result.RESULT_TRUE_PROP,
            "UNKNOWN": result.RESULT_UNKNOWN,
            "FALSE": result.RESULT_FALSE_REACH,
            "FALSE(valid-memtrack)": result.RESULT_FALSE_MEMTRACK,
            "FALSE(valid-deref)": result.RESULT_FALSE_DEREF,
            "FALSE(valid-free)": result.RESULT_FALSE_FREE,
        }

        for p in possible_outputs:
            for o in output:
                if p in o:
                    return results[p]
        return result.RESULT_UNKNOWN
