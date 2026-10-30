# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2026 Álvaro Borrás
#
# SPDX-License-Identifier: MIT
import math

from benchexec import result
from benchexec.tools.template import BaseTool2


class Tool(BaseTool2):
    REQUIRED_PATHS = [
        "bin/adaptivesv",
        "src",
        "configs",
        "vendor",
        "third_party/CPAchecker-4.2.2-unix",
    ]

    def name(self):
        return "AdaptiveSV"

    def project_url(self):
        return "https://gitlab.com/alexbf/adaptivesv"

    def executable(self, tool_locator):
        return tool_locator.find_executable("adaptivesv", subdir="bin")

    def version(self, executable):
        return (
            self._version_from_tool(executable)
            .removeprefix("AdaptiveSV ")
            .split(" ", 1)[0]
        )

    def program_files(self, executable):
        return self._program_files_from_executable(
            executable, self.REQUIRED_PATHS, parent_dir=True
        )

    def cmdline(self, executable, options, task, rlimits):
        args = [executable, *options]

        def has_option(option):
            return any(
                arg == option or arg.startswith(option + "=") for arg in options
            )

        if not has_option("--program") and task.single_input_file:
            args += ["--program", task.single_input_file]

        if not has_option("--property") and task.property_file:
            args += ["--property", task.property_file]

        if not has_option("--architecture"):
            metadata = task.options or {}
            model = metadata.get("data_model") if isinstance(metadata, dict) else None
            architecture = {"ILP32": "32", "LP64": "64"}.get(model)
            if architecture:
                args += ["--architecture", architecture]

        if not has_option("--time-limit") and rlimits.cputime:
            args += ["--time-limit", str(max(1, math.floor(rlimits.cputime)))]
        return args

    def determine_result(self, run):
        if run.exit_code:
            return result.RESULT_ERROR
        answers = [
            line
            for line in run.output
            if line in ("TRUE", "FALSE(unreach-call)", "UNKNOWN")
        ]
        if len(answers) != 1:
            return result.RESULT_ERROR
        return {
            "TRUE": result.RESULT_TRUE_PROP,
            "FALSE(unreach-call)": result.RESULT_FALSE_REACH,
            "UNKNOWN": result.RESULT_UNKNOWN,
        }[answers[0]]
