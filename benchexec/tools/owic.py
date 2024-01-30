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
    This class serves as tool adaptor for Owi
    """

    def executable(self, tool_locator):
        return tool_locator.find_executable("owic", subdir="bin")

    def version(self, executable):
        return self._version_from_tool(executable, "--version")

    def name(self):
        return "Owi"

    def project_url(self):
        return "https://github.com/OCamlPro/owi"

    def cmdline(self, executable, options, task, _):
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
        if run.exit_code == 1:
            return result.RESULT_ERROR

        for line in run.output:
            if "Assert failure" in line:
                return result.RESULT_FALSE_REACH
            elif "ERROR" in line:
                return result.RESULT_ERROR
            elif "All OK" in line:
                return result.RESULT_DONE

        if run.was_timeout:
            return result.RESULT_TIMEOUT
        return result.RESULT_UNKNOWN
