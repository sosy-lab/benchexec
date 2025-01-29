# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.tools.cpachecker as cpachecker

from benchexec.tools.template import ToolNotFoundException, UnsupportedFeatureException


class Tool(cpachecker.Tool):
    """Tool info for PeSCo."""

    REQUIRED_PATHS_v1 = list(cpachecker.Tool.REQUIRED_PATHS) + ["resources"]
    REQUIRED_PATHS_v2 = ["bin/*.py", "lib", "properties"]

    def executable(self, tool_locator):
        try:
            executable = tool_locator.find_executable("pesco", subdir="bin")
            self._version = 2
            self.REQUIRED_PATHS = self.REQUIRED_PATHS_v2
        except ToolNotFoundException:
            self.REQUIRED_PATHS = self.REQUIRED_PATHS_v1
            executable = super().executable(tool_locator)
            self._version = 1

        return executable

    def version(self, executable):
        if self._version == 1:
            return super().version(executable)
        version = self._version_from_tool(executable, "--version", line_prefix="PeSCo")

        pesco_version, *cpa_version = version.split(" ")
        return "+".join([pesco_version, cpa_version[1]])

    def _additional_options(self, existing_options, task, rlimits):
        options = []
        if rlimits.cputime and "--timelimit" not in existing_options:
            options += ["--timelimit", str(rlimits.cputime)]

        if task.property_file:
            options += ["--spec", task.property_file]

        if isinstance(task.options, dict) and task.options.get("language") == "C":
            data_model = task.options.get("data_model")
            if data_model:
                data_model_option = {"ILP32", "LP64"}
                if data_model in data_model_option:
                    if "--data_model" not in existing_options:
                        options += ["--data_model", data_model]
                else:
                    raise UnsupportedFeatureException(
                        f"Unsupported data_model '{data_model}' defined for task '{task}'"
                    )

        return options

    def cmdline(self, executable, options, task, rlimits):
        if self._version == 1:
            return super().cmdline(executable, options, task, rlimits)

        additional_options = self._additional_options(options, task, rlimits)

        return (
            [executable]
            + options
            + additional_options
            + list(task.input_files_or_identifier)
        )

    def name(self):
        return "PeSCo"
