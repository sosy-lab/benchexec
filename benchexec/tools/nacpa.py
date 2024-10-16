# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

from benchexec import result
from benchexec.tools import template


class Tool(template.BaseTool2):
    """
    Tool-info module for nacpa, a parallel portfolio
    of natively compiled CPAchecker instances.
    """

    REQUIRED_PATHS = ["bin", "lib"]

    def executable(self, tool_locator):
        return tool_locator.find_executable("nacpa", subdir="bin")

    def version(self, executable):
        return self._version_from_tool(
            executable, "--version", line_prefix="nacpa version"
        )

    def program_files(self, executable):
        return self._program_files_from_executable(
            executable, self.REQUIRED_PATHS, parent_dir=True
        )

    def name(self):
        return "nacpa"

    def project_url(self):
        return "https://gitlab.com/sosy-lab/software/nacpa"

    def cmdline(self, executable, options, task, rlimits):
        if "--spec" not in options and task.property_file:
            options = options + ["--spec", task.property_file]

        if (
            "--data-model" not in options
            and isinstance(task.options, dict)
            and task.options.get("language") == "C"
        ):
            data_model = task.options.get("data_model")
            if data_model:
                options = options + ["--data-model", data_model]

        return [executable, *options, task.single_input_file]

    def determine_result(self, run):
        for line in reversed(run.output):
            if line.startswith("VERDICT: "):
                verdict = line.partition(":")[-1].strip().lower()
                if verdict.lower().startswith("true"):
                    return result.RESULT_TRUE_PROP
                elif verdict.lower().startswith("false(unreach-call)"):
                    return result.RESULT_FALSE_REACH
                elif verdict.lower().startswith("false(termination)"):
                    return result.RESULT_FALSE_TERMINATION
                elif verdict.lower().startswith("false(no-overflow)"):
                    return result.RESULT_FALSE_OVERFLOW
                elif verdict.lower().startswith("false(no-deadlock)"):
                    return result.RESULT_FALSE_DEADLOCK
                elif verdict.lower().startswith("false(valid-deref)"):
                    return result.RESULT_FALSE_DEREF
                elif verdict.lower().startswith("false(valid-free)"):
                    return result.RESULT_FALSE_FREE
                elif verdict.lower().startswith("false(valid-memtrack)"):
                    return result.RESULT_FALSE_MEMTRACK
                elif verdict.lower().startswith("false(valid-memcleanup)"):
                    return result.RESULT_FALSE_MEMCLEANUP
                elif verdict.lower().startswith("false"):
                    return result.RESULT_FALSE_PROP
        return result.RESULT_UNKNOWN

    def get_value_from_output(self, output, identifier):
        for line in output:
            if line.lstrip().startswith(identifier):
                startPosition = line.find(":") + 1
                endPosition = line.find("(", startPosition)

                if endPosition == -1:
                    endPosition = len(line)

                return line[startPosition:endPosition].strip()

        return None
