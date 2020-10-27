# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import os
import benchexec.util as util
import benchexec.tools.template
import benchexec.result as result


class Tool(benchexec.tools.template.BaseTool2):
    """
    This class serves as tool adaptor for ESBMC (http://www.esbmc.org/)
    """

    REQUIRED_PATHS = ["cpachecker", "esbmc", "esbmc-wrapper.py", "tokenizer"]

    def executable(self, tool_locator):
        return tool_locator.find_executable("esbmc-wrapper.py")

    def working_directory(self, executable):
        executableDir = os.path.dirname(executable)
        return executableDir

    def version(self, executable):
        return self._version_from_tool(executable, "-v")

    def name(self):
        return "ESBMC"

    def cmdline(self, executable, options, task, rlimits):
        data_model_param = util.get_data_model_from_task(
            task, {"ILP32": "32", "LP64": "64"}
        )
        if data_model_param and "--arch" not in options:
            options += ["--arch", data_model_param]
        return (
            [executable]
            + ["-p", task.property_file]
            + options
            + [task.single_input_file]
        )

    def determine_result(self, run):
        output = "\n".join(run.output)
        status = result.RESULT_UNKNOWN

        if self.allInText(["FALSE_DEREF"], output):
            status = result.RESULT_FALSE_DEREF
        elif self.allInText(["FALSE_FREE"], output):
            status = result.RESULT_FALSE_FREE
        elif self.allInText(["FALSE_MEMTRACK"], output):
            status = result.RESULT_FALSE_MEMTRACK
        elif self.allInText(["FALSE_OVERFLOW"], output):
            status = result.RESULT_FALSE_OVERFLOW
        elif self.allInText(["FALSE_TERMINATION"], output):
            status = result.RESULT_FALSE_TERMINATION
        elif self.allInText(["FALSE"], output):
            status = result.RESULT_FALSE_REACH
        elif "TRUE" in output:
            status = result.RESULT_TRUE_PROP
        elif "DONE" in output:
            status = result.RESULT_DONE

        if status == result.RESULT_UNKNOWN:
            if run.was_timeout:
                status = "TIMEOUT"
            elif output.endswith(("error", "error\n")):
                status = "ERROR"

        return status

    """ helper method """

    def allInText(self, words, text):
        """
        This function checks, if all the words appear in the given order in the text.
        """
        index = 0
        for word in words:
            index = text[index:].find(word)
            if index == -1:
                return False
        return True
