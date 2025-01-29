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
    Tool info for FDSE.
    """

    def executable(self, tool_locator):
        return tool_locator.find_executable("fdse")

    def version(self, executable):
        return self._version_from_tool(executable, "-v")

    def cmdline(self, executable, options, task, rlimits):
        new_option = []
        if task.property_file:
            new_option += [f"--property-file={task.property_file}"]
        if rlimits.cputime:
            new_option += [f"-mt={rlimits.cputime}"]

        new_option += [f"-sf={task.single_input_file}"]
        return [executable] + new_option + options

    def name(self):
        return "FDSE"

    def project_url(self):
        return "https://github.com/passengerZ/FDSE"

    def determine_result(self, run):
        status = result.RESULT_ERROR

        for line in run.output:
            if "Done : End analysis" in line:
                status = result.RESULT_DONE
            elif "HaltTimer invoked!!!" in line:
                status = result.RESULT_TIMEOUT

        return status
