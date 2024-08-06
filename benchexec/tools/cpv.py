# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.result as result
import benchexec.tools.template


class Tool(benchexec.tools.template.BaseTool2):
    """
    Tool info for CPV: A circuit-based program verifier for C
    """

    REQUIRED_PATHS = [
        "actors/",
        "bin/",
        "cpv/",
        "lib/",
        "kratos2/",
    ]

    def executable(self, tool_locator):
        return tool_locator.find_executable("cpv", subdir="bin")

    def name(self):
        return "CPV"

    def project_url(self):
        return "https://gitlab.com/sosy-lab/software/cpv"

    def version(self, executable):
        return self._version_from_tool(executable)

    def program_files(self, executable):
        return self._program_files_from_executable(
            executable, self.REQUIRED_PATHS, parent_dir=True
        )

    def cmdline(self, executable, options, task, rlimits):
        assert task.options.get("language") == "C"
        options += ["--property", task.property_file]
        if task.options.get("data_model") and "--model" not in options:
            options += ["--model", task.options.get("data_model")]
        return [executable, task.single_input_file, *options]

    def determine_result(self, run):
        if run.was_timeout:
            return result.RESULT_TIMEOUT
        for line in run.output[::-1]:
            if line.startswith("INFO: Verification result:"):
                if "TRUE" in line:
                    return result.RESULT_TRUE_PROP
                if "FALSE" in line:
                    return result.RESULT_FALSE_REACH
                if "UNKNOWN" in line:
                    return result.RESULT_UNKNOWN
                if "ERROR" in line:
                    return result.RESULT_ERROR + "(verification failed)"
            if line.startswith("cpv.task_translator.TranslationFailedError"):
                return result.RESULT_ERROR + "(translation failed)"
        return result.RESULT_ERROR
