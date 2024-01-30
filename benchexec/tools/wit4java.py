# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.tools.template
import benchexec.result as result
from benchexec.tools.template import ToolNotFoundException


class Tool(benchexec.tools.template.BaseTool2):
    """
    Tool info for wit4java
    """

    def executable(self, tool_locator):
        try:
            return tool_locator.find_executable("wit4java-wrapper.py")
        except ToolNotFoundException:
            return tool_locator.find_executable("wit4java.py")

    def version(self, executable):
        return self._version_from_tool(executable)

    def name(self):
        return "wit4java"

    def project_url(self):
        return "https://github.com/wit4java/wit4java"

    def cmdline(self, executable, options, task, rlimits):
        return [executable] + options + list(task.input_files)

    def determine_result(self, run):
        output = run.output
        version = 1.0
        for line in output:
            if "wit4java version: " in line:
                version = float(line[line.index("wit4java version: ") + 18 :])
                break
        if version >= 3.0:
            for line in output:
                if "wit4java: Witness Correct" in line:
                    return result.RESULT_FALSE_PROP

                if "wit4java: Witness Spurious" in line:
                    return result.RESULT_TRUE_PROP

                if "wit4java: Could not validate witness" in line:
                    return result.RESULT_UNKNOWN
        else:
            validation = "unknown"
            for line in output:
                if "Exception" in line:
                    if "AssertionError" in line:
                        validation = "false"
                    else:
                        validation = "unknown"
                    break
                else:
                    validation = "true"

            if validation == "false":
                status = result.RESULT_FALSE_PROP

            elif validation == "true":
                status = result.RESULT_TRUE_PROP

            elif validation == "unknown":
                status = result.RESULT_UNKNOWN
            else:
                status = result.RESULT_ERROR
            return status

        return result.RESULT_ERROR
