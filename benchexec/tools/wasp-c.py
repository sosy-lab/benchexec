# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.tools.template
import benchexec.result as result

from benchexec.tools.sv_benchmarks_util import get_data_model_from_task, ILP32, LP64


class Tool(benchexec.tools.template.BaseTool2):
    """
    This class serves as tool adaptor for WASP-C
    """

    def executable(self, tool_locator):
        return tool_locator.find_executable("wasp-c", subdir="bin")

    def version(self, executable):
        return self._version_from_tool(executable, "-v")

    def name(self):
        return "WASP-C"

    def project_url(self):
        return "https://github.com/wasp-platform/wasp"

    def cmdline(self, executable, options, task, rlimits):
        if task.property_file:
            options = options + ["--property", task.property_file]
        else:
            raise benchexec.tools.template.UnsupportedFeatureException(
                "property file is required"
            )

        data_model_param = get_data_model_from_task(task, {ILP32: "32", LP64: "64"})
        if data_model_param and "--arch" not in options:
            options += ["--arch", data_model_param]

        return [executable] + options + [task.single_input_file]

    def determine_result(self, run):
        if (
            run.exit_code == 1
            or run.output.any_line_contains("Failed to")
            or run.output.any_line_contains("WASP crashed")
        ):
            return result.RESULT_ERROR
        elif run.was_timeout or run.output.any_line_contains("WASP timed out"):
            return result.RESULT_TIMEOUT
        elif run.exit_code == 0 and run.output.any_line_contains("Analysis done."):
            return result.RESULT_DONE
        else:
            return result.RESULT_UNKNOWN
