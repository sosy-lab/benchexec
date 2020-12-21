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
    """     Tool info for IGML
       The tool will be available soon"""

    REQUIRED_PATHS = [
        "lib/*.jar",
        "scripts",
        "igml-deps.jar"
    ]

    def executable(self, tool_locator):
        executable = tool_locator.find_executable("igml.sh", subdir="scripts")
        base_dir = os.path.join(os.path.dirname(executable), os.path.pardir)
        jar_file = os.path.join(base_dir, "igml-deps.jar")
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

        try:
            options += ["-f", task.single_input_file]
        except benchexec.tools.template.UnsupportedFeatureException:
            raise benchexec.tools.template.UnsupportedFeatureException(
                "Unsupported task with multiple input files for task '{}'".format(task))

        if isinstance(task.options, dict) and task.options.get("language") == "C":
            data_model = task.options.get("data_model")
            if data_model:
                data_model_option = get_data_model_from_task(task, {ILP32: "-m 32", LP64: "-m 64"})
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
        return (
                [executable]
                + options
                + additional_options
        )

    def determine_result(self, run):
        """
        @return: status of IGML after executing a run
        """

        status = None

        for line in run.output:
            if "IMGLs FINAL RESULT:" in line:
                if "incorrect" in line:
                    return result.RESULT_FALSE_PROP
                else:
                    return result.RESULT_TRUE_PROP
            if "Cannot check validity of the computed invariant!" in line:
                return result.RESULT_UNKNOWN + "(No oracle)"
        return result.RESULT_UNKNOWN
