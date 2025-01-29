#!/usr/bin/env python

# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.result as result
import benchexec.util as util
import benchexec.tools.template


class Tool(benchexec.tools.template.BaseTool):
    """
    Tool info for HIPrec.
    """

    REQUIRED_PATHS = [
        "fixcalc",
        "hiprec",
        "hiprec_run.sh",
        "oc",
        "prelude.ss",
        "z3-4.3.2",
    ]

    def executable(self):
        executable = util.find_executable("hiprec")
        return executable

    def name(self):
        return "HIPrec"

    def cmdline(self, executable, options, tasks, propertyfile=None, rlimits={}):
        return [executable] + options + tasks + ["--debug"]

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        status = result.RESULT_UNKNOWN
        for line in output:
            if line.startswith("Verification result:("):
                line = line[21:].strip()
                if line.startswith("TRUE"):
                    status = result.RESULT_TRUE_PROP
                elif line.startswith("FALSE"):
                    status = result.RESULT_FALSE_REACH
                else:
                    status = result.RESULT_UNKNOWN

        return status
