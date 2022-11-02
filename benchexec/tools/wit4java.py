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
    Tool info for wit4java
    (https://github.com/wit4java/wit4java).
    """

    def executable(self, tool_locator):
        return tool_locator.find_executable("wit4java")

    def version(self, executable):
        return self._version_from_tool(executable)

    def name(self):
        return "wit4java"

    def cmdline(self, executable, options, task, rlimits):
        input_files =  list(task.input_files)
        benchmark = input_files[-1]
        packages = input_files[0:-1]
        return [executable] + [benchmark] + ['--packages'] +  packages + options

    def determine_result(self, run):
        output = run.output
        for line in output:
            if 'wit4java: Witness Correct' in line:
                return result.RESULT_FALSE_PROP

            if 'wit4java: Witness Spurious' in line:
                return result.RESULT_TRUE_PROP

            if 'wit4java: Could not validate witness' in line:
                return result.RESULT_UNKNOWN

        return result.RESULT_ERROR
