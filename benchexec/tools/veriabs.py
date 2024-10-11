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
    VeriAbs
    """

    REQUIRED_PATHS = [
        "bin",
        "cpact",
        "jars",
        "exp-in",
        "prism",
        "lib",
        "afl-2.35b",
        "verifuzz",
        "afl-2.35b_v1",
        "frama-c-Chlorine-20180502",
        "UAutomizer-linux",
        "scripts",
        "supportFiles",
    ]

    def executable(self, tool_locator):
        return tool_locator.find_executable("veriabs", subdir="scripts")

    def version(self, executable):
        return self._version_from_tool(executable)

    def program_files(self, executable):
        return self._program_files_from_executable(
            executable, self.REQUIRED_PATHS, parent_dir=True
        )

    def name(self):
        return "VeriAbs"

    def project_url(self):
        return "https://doi.org/10.5281/zenodo.10066250"

    def cmdline(self, executable, options, task, rlimits):
        if task.property_file:
            options += ["--property-file", task.property_file]
        data_model_param = get_data_model_from_task(task, {ILP32: "-32", LP64: "-64"})
        if data_model_param and data_model_param not in options:
            options += [data_model_param]
        return [executable] + options + [task.single_input_file]

    def determine_result(self, run):
        if run.output.any_line_contains("VERIABS_VERIFICATION_SUCCESSFUL"):
            return result.RESULT_TRUE_PROP
        elif run.output.any_line_contains("VERIABS_VERIFICATION_FAILED"):
            return result.RESULT_FALSE_REACH
        elif run.output.any_line_contains("VERIABS_UNKNOWN"):
            return result.RESULT_UNKNOWN
        elif run.output.any_line_contains("NOT SUPPORTED"):
            return result.RESULT_UNKNOWN
        return result.RESULT_ERROR
