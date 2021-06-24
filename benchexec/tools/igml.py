# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import logging
import os
import re
import sys

import benchexec.result as result
import benchexec.tools.template
import benchexec.tools.template
from benchexec.tools.sv_benchmarks_util import get_data_model_from_task, ILP32, LP64


class Tool(benchexec.tools.template.BaseTool2):
    """Tool info for IGML
    The tool will be available soon"""

    REQUIRED_PATHS = ["lib/*.jar", "scripts", "igml.jar"]

    def executable(self, tool_locator):
        executable = tool_locator.find_executable("igml.sh", subdir="scripts")
        base_dir = os.path.join(os.path.dirname(executable), os.path.pardir)
        jar_file = os.path.join(base_dir, "igml.jar")
        bin_dir = os.path.join(base_dir, "target")
        src_dir = os.path.join(base_dir, "src")
        return executable

    def program_files(self, executable):
        return self._program_files_from_executable(
            executable, self.REQUIRED_PATHS, parent_dir=True
        )

    def version(self, executable):
        return self._version_from_tool(executable)

    def name(self):
        return "IGML"

    def _get_additional_options(self, existing_options, task, rlimits):
        options = []
        if rlimits.cputime and "-timelimit" not in existing_options:
            options += ["-timelimit", str(rlimits.cputime)]

        if task.property_file:
            options += ["-p", task.property_file]

        # try:
        #     options += ["-f", task.single_input_file]
        # except benchexec.tools.template.UnsupportedFeatureException:
        #     raise benchexec.tools.template.UnsupportedFeatureException(
        #         "Unsupported task with multiple input files for task '{}'".format(task)
        # )

        if isinstance(task.options, dict) and task.options.get("language") == "C":
            data_model = task.options.get("data_model")
            if data_model:
                data_model_option = get_data_model_from_task(
                    task, {ILP32: "-m 32", LP64: "-m 64"}
                )
                if data_model_option:
                    if data_model_option not in existing_options:
                        options += [data_model_option]
                else:
                    raise benchexec.tools.template.UnsupportedFeatureException(
                        "Unsupported data_model '{}' defined for task '{}'".format(
                            data_model, task
                        )
                    )
        return options

    def cmdline(self, executable, options, task, rlimits):
        additional_options = self._get_additional_options(options, task, rlimits)
        return [executable] + options + additional_options

    def determine_result(self, run):
        """
        @return: status of IGML after executing a run
        """
        for line in run.output:
            if "IMGLs FINAL RESULT:" in line:
                if (
                    "Correct_True" in line
                    or "Correct_False" in line
                    or "Valid_Inv" in line
                    or "Invalid_Inv" in line
                    or "Trivial_Inv" in line
                ):
                    return result.CATEGORY_CORRECT
                elif "False_Positive" in line or "False_Negative":
                    return result.CATEGORY_WRONG
                elif "Unknown" in line:
                    return result.CATEGORY_UNKNOWN
                elif "Aborted" in line:
                    return result.CATEGORY_ERROR + "(Aborted)"
                elif "Timeout" in line:
                    return result.CATEGORY_ERROR + "(Timeout)"
        return result.CATEGORY_UNKNOWN

    def get_value_from_output(self, output, identifier):
        match = None
        for line in output:
            if line.lstrip().startswith(identifier):
                startPosition = line.find(":") + 1
                endPosition = line.find("(", startPosition)
                if endPosition == -1:
                    endPosition = len(line)
                if match is None:
                    match = line[startPosition:endPosition].strip()
                else:
                    logging.warning(
                        "skipping repeated match for identifier '%s': '%s'",
                        identifier,
                        line,
                    )
        return match
