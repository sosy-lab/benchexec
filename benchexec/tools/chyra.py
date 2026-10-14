# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.tools.template
from benchexec import result
from benchexec.tools.sv_benchmarks_util import ILP32, LP64, get_data_model_from_task


class Tool(benchexec.tools.template.BaseTool2):
    """Tool info for Chyra's concurrent C verifier with YAML witness export."""

    REQUIRED_PATHS = [
        "chyra-verifier",
        "chyra",
        "graphml_correctness_to_yaml.py",
        "loop_create_filter.awk",
        "multi_create_loop_filter.awk",
    ]

    def executable(self, tool_locator):
        return tool_locator.find_executable("chyra-wrapper")

    def name(self):
        return "Chyra"

    def version(self, executable):
        return self._version_from_tool(executable, arg="--version")

    def project_url(self):
        return "https://gitlab.com/Lapulatos/chyra"

    def cmdline(self, executable, options, task, rlimits):
        if not task.property_file:
            raise benchexec.tools.template.UnsupportedFeatureException(
                "Chyra requires a property file"
            )
        arguments = list(options)
        model = get_data_model_from_task(task, {ILP32: "--32", LP64: "--64"})
        if model:
            if model not in arguments:
                arguments.append(model)
        return [executable, task.property_file, task.single_input_file] + arguments

    def determine_result(self, run):
        if run.was_timeout or run.exit_code.signal or run.exit_code.value:
            return result.RESULT_ERROR
        if not run.output:
            return result.RESULT_ERROR
        terminal = run.output[-1]
        if terminal == "UNKNOWN":
            return result.RESULT_UNKNOWN
        if terminal == "VERIFICATION SUCCESSFUL":
            return result.RESULT_TRUE_PROP
        if terminal == "VERIFICATION FAILED":
            results = {
                "CHYRA_RESULT: false(unreach-call)": result.RESULT_FALSE_REACH,
                "CHYRA_RESULT: false(no-data-race)": result.RESULT_FALSE_DATARACE,
                "CHYRA_RESULT: false(no-overflow)": result.RESULT_FALSE_OVERFLOW,
                "CHYRA_RESULT: false(valid-memtrack)": result.RESULT_FALSE_MEMTRACK,
                "CHYRA_RESULT: false(valid-deref)": result.RESULT_FALSE_DEREF,
                "CHYRA_RESULT: false(valid-free)": result.RESULT_FALSE_FREE,
            }
            for line in run.output:
                if line.startswith("CHYRA_RESULT:"):
                    return results.get(line, result.RESULT_ERROR)
        return result.RESULT_ERROR
