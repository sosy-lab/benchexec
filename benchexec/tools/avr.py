# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.result as result
import benchexec.tools.template


class Tool(benchexec.tools.template.BaseTool2):
    """
    Tool info for AVR -- Abstractly Verifying Reachability
    URL: https://github.com/aman-goel/avr
    """

    def executable(self, tool_locator):
        return tool_locator.find_executable("avr.py")

    def name(self):
        return "AVR"

    def cmdline(self, executable, options, task, rlimits):
        return [executable] + options + [task.single_input_file]

    def determine_result(self, run):
        """
        @return: status of AVR after executing a run
        """
        if run.was_timeout:
            return result.RESULT_TIMEOUT
        for line in run.output:
            # skip the lines that do not contain verification result
            if not line.startswith("Verification result:"):
                continue
            if "avr-h" in line:
                return result.RESULT_TRUE_PROP
            elif "avr-v" in line:
                return result.RESULT_FALSE_PROP
        return result.RESULT_ERROR
