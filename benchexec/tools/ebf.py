# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import os
from benchexec.tools.sv_benchmarks_util import get_data_model_from_task, ILP32, LP64
import benchexec.tools.template
import benchexec.result as result


class Tool(benchexec.tools.template.BaseTool2):
    """
    This class serves as tool adaptor for EBF
    """

    def executable(self, tool_locator):
        return tool_locator.find_executable("RunEBF.py", subdir="scripts")

    def working_directory(self, executable):
        executableDir = os.path.dirname(executable)
        return executableDir

    def version(self, executable):
        return self._version_from_tool(executable, "-v")

    def name(self):
        return "EBF"

    def project_url(self):
        return "https://github.com/fatimahkj/EBF"

    def cmdline(self, executable, options, task, rlimits):
        data_model_param = get_data_model_from_task(task, {ILP32: "32", LP64: "64"})
        if data_model_param and "--arch" not in options:
            options += ["-a", data_model_param]
        if not task.property_file:
            raise benchexec.tools.template.UnsupportedFeatureException(
                "Property file required"
            )
        return (
            [executable]
            + ["-p", task.property_file]
            + options
            + [task.single_input_file]
        )

    def determine_result(self, run):
        status = "ERROR"

        if run.output.any_line_contains("FALSE(reach)"):
            status = result.RESULT_FALSE_REACH
        elif run.output.any_line_contains("VERIFICATION TRUE"):
            status = result.RESULT_TRUE_PROP
        elif run.output.any_line_contains("UNKNOWN"):
            status = result.RESULT_UNKNOWN
        return status
