# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2025 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import re
from functools import cache

import benchexec.result as result
import benchexec.tools.template


class Tool(benchexec.tools.template.BaseTool2):
    # Required paths are relative to the tool directory.
    REQUIRED_PATHS = ["afl-distribution/", "harness/", "seeds/", "bin/fuzz-to-tc"]

    def executable(self, tool_locator):
        return tool_locator.find_executable("afl-tc", subdir="bin")

    @cache
    def version(self, executable):
        return self._version_from_tool(
            executable, arg="--version", line_prefix="afl-tc version"
        )

    def program_files(self, executable):
        return self._program_files_from_executable(
            executable=executable, required_paths=self.REQUIRED_PATHS, parent_dir=True
        )

    def environment(self, executable):
        return {
            "newEnv": {
                "AFL_SKIP_CPUFREQ": "1",  # Required to run on BenchCloud
            }
        }

    def name(self):
        return "afl-tc"

    def project_url(self):
        return "https://gitlab.com/sosy-lab/software/test-to-witness"

    def cmdline(self, executable, options, task, rlimits):
        task_options = task.options or {}

        data_model = None
        if isinstance(task_options, dict):
            data_model = task_options.get("data_model", None)

        if data_model is None:
            raise ValueError("The 'data_model' option must be specified for afl-tc.")

        data_model_option = {"ILP32": "32bit", "LP64": "64bit"}.get(data_model)

        if data_model_option is None:
            raise ValueError(
                "The 'data_model' option must be either 'ILP32' or 'LP64'."
            )

        command_line = [executable, task.single_input_file, data_model_option]

        # The first version(s) (all denoted as "0.1.0") did not support property files
        version = self.version(executable)
        if version == "0.1.0":
            return command_line

        if task.property_file is None:
            raise ValueError(
                "For versions not being 0.1.0 a property file must be specified for afl-tc."
            )

        command_line += [task.property_file]
        return command_line

    def determine_result(self, run):
        ansi_escape = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
        for line in reversed(run.output):
            # Remove ANSI escape sequences (terminal control characters)
            clean_line = ansi_escape.sub("", line)
            if "Processing complete. Results available" in clean_line:
                return result.RESULT_DONE

        return result.RESULT_ERROR
