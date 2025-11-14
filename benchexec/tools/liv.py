# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import logging
import re
from typing import Optional

import benchexec.result
from benchexec.tools.metaval import (
    MetavalVersionGreaterThanOrEqualTwo,
    is_version_less_than_two,
)
from benchexec.tools.template import BaseTool2, ToolNotFoundException
from benchexec.tools.sv_benchmarks_util import (
    ILP32,
    LP64,
    get_data_model_from_task,
    TaskFilesConsidered,
    handle_witness_of_task,
)


class LivVersionLessThanTwo:
    REQUIRED_PATHS = ["liv", "lib", "bin", "actors", ".venv"]

    def program_files(self, executable):
        return [executable] + BaseTool2._program_files_from_executable(
            executable, self.REQUIRED_PATHS, parent_dir=True
        )

    def cmdline(self, executable, options, task, rlimits):
        if task.property_file:
            options = options + ["--property", task.property_file]

        data_model_param = get_data_model_from_task(
            task, {ILP32: "ILP32", LP64: "LP64"}
        )

        if data_model_param and "--data-model" not in options:
            options += ["--data-model", data_model_param]

        input_files, witness_options = handle_witness_of_task(
            task,
            options,
            "--witness",
            TaskFilesConsidered.INPUT_FILES_OR_IDENTIFIER,
        )

        return [executable] + options + witness_options + input_files

    def determine_result(self, run):
        if not run.output:
            return benchexec.result.RESULT_ERROR
        lastline = run.output[-1]
        if lastline.startswith("Overall result: true"):
            status = benchexec.result.RESULT_TRUE_PROP
        elif lastline.startswith("Overall result: false"):
            status = benchexec.result.RESULT_FALSE_PROP
        elif lastline.startswith("Overall result: unknown"):
            status = benchexec.result.RESULT_UNKNOWN
        else:
            status = benchexec.result.RESULT_ERROR
        match = re.match(r".*\((.*)\)", lastline)
        if match:
            status += f"({match.group(1)})"
        return status

    def get_value_from_output(self, output, identifier):
        # search for the text in output and get its value,
        # search the first line, that starts with the searched text
        # warn if there are more lines (multiple statistics from sequential analysis?)
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


class Tool(BaseTool2):
    """
    Tool info for LIV.
    """

    def __init__(self):
        self._cached_version: Optional[str] = None
        self._original_liv = LivVersionLessThanTwo()
        self._metaval_liv = MetavalVersionGreaterThanOrEqualTwo()

    def version(self, executable):
        """
        Get version string from the tool output.
        This version string is cached after the first call.
        It cannot be cached using @functools.lru_cache because the
        executable is an argument, which can be None.
        """
        if self._cached_version is None:
            self._cached_version = self._version_from_tool(executable, "--version")

        return self._cached_version

    def executable(self, tool_locator: BaseTool2.ToolLocator):
        try:
            return tool_locator.find_executable("liv", subdir="bin")
        except ToolNotFoundException as e1:
            try:
                return tool_locator.find_executable("metaval.py")
            except ToolNotFoundException:
                raise e1

    def program_files(self, executable):
        return [executable] + self._program_files_from_executable(
            executable, self.REQUIRED_PATHS, parent_dir=True
        )

    def name(self):
        return "LIV"

    def project_url(self):
        return "https://gitlab.com/sosy-lab/software/liv"

    def cmdline(self, executable, options, task, rlimits):
        if is_version_less_than_two(self, executable):
            return self._original_liv.cmdline(executable, options, task, rlimits)
        else:
            return self._metaval_liv.cmdline(executable, options, task, rlimits)

    def determine_result(self, run):
        if is_version_less_than_two(self, None):
            return self._original_liv.determine_result(run)
        else:
            return self._metaval_liv.determine_result(run)

    def get_value_from_output(self, output, identifier):
        if is_version_less_than_two(self, None):
            return self._original_liv.get_value_from_output(output, identifier)
        else:
            return self._metaval_liv.get_value_from_output(output, identifier)
