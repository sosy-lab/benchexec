# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2023 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.tools.template
import benchexec.result as result

import re


class Tool(benchexec.tools.template.BaseTool2):
    """
    Tool info for sanitizers via SV-COMP wrapper.
    """

    def executable(self, tool_locator):
        return tool_locator.find_executable("sv-sanitizers.py")

    def version(self, executable):
        return self._version_from_tool(executable)

    def name(self):
        return "sv-sanitizers"

    def project_url(self):
        return "https://github.com/sim642/sv-sanitizers/"

    def cmdline(self, executable, options, task, rlimits):
        additional_options = []

        if task.property_file:
            additional_options += ["--property", task.property_file]

        if task.options:
            data_model = task.options.get("data_model")
            if data_model:
                additional_options += [
                    "--data-model",
                    data_model,
                ]

        return [
            executable,
            *options,
            *additional_options,
            task.single_input_file,
        ]

    def determine_result(self, run):
        status = None

        for line in run.output:
            if "Traceback (most recent call last)" in line:
                return "EXCEPTION"
            else:
                m = re.match(r"SV-COMP result: (.*)", line)
                if m:
                    status = m.group(1)

        if status:
            return status

        if run.exit_code.value != 0:
            return result.RESULT_ERROR
        else:
            return result.RESULT_UNKNOWN
