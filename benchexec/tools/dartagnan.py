# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.tools.template
import benchexec.result as result


class Tool(benchexec.tools.template.BaseTool2):
    """
    Tool info for Dartagnan.
    """

    def executable(self, tool_locator):
        return tool_locator.find_executable("Dartagnan-SVCOMP.sh")

    def name(self):
        return "Dartagnan"

    def project_url(self):
        return "https://github.com/hernanponcedeleon/Dat3M"

    def cmdline(self, executable, options, task, rlimits):
        if task.property_file:
            options += [task.property_file]
        return [executable] + options + list(task.input_files_or_identifier)

    def version(self, executable):
        return self._version_from_tool(executable)

    def determine_result(self, run):
        status = result.RESULT_ERROR
        if run.output:
            result_str = run.output[-1].strip()
            if "FAIL" in result_str:
                failure_str = run.output[-3].strip()
                if "integer overflow" in failure_str:
                    status = result.RESULT_FALSE_OVERFLOW
                elif "invalid dereference" in failure_str:
                    status = result.RESULT_FALSE_DEREF
                elif "user assertion" in failure_str:
                    status = result.RESULT_FALSE_REACH
                else:
                    status = result.RESULT_FALSE_PROP
            elif "PASS" in result_str:
                status = result.RESULT_TRUE_PROP
            elif "UNKNOWN" in result_str:
                status = result.RESULT_UNKNOWN
        return status

    def program_files(self, executable):
        return [executable] + self.REQUIRED_PATHS
