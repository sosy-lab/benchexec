# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import logging
import re

import benchexec.result
from benchexec.tools.metaval import (
    MetaVal2,
)
from benchexec.tools.template import BaseTool2, ToolNotFoundException
from benchexec.tools.sv_benchmarks_util import (
    ILP32,
    LP64,
    get_data_model_from_task,
    TaskFilesConsidered,
    handle_witness_of_task,
)


class Liv0:
    REQUIRED_PATHS = ["liv", "lib", "bin", "actors", ".venv"]

    def executable(self, tool_locator: BaseTool2.ToolLocator):
        return tool_locator.find_executable("liv", subdir="bin")

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

    After the first development version of LIV (version 0.x),
    realization came that it share a large part of the codebase with MetaVal.
    Therefore, LIV version 2.0 and later is implemented inside MetaVal,
    using its command line interface and output format.
    This Tool module delegates calls to the appropriate implementation
    depending on the detected LIV version.

    In addition, it was desired that both LIV and MetaVal run independently
    at SV-COMP, i.e., both tools should be run independently.

    Since meeting these requirements in a single Tool module is not possible
    due to technical limitations of FM-Tools,
    this Tool module uses delegation to two different implementations
    depending on the detected LIV version.
    """

    def __init__(self):
        self._delegate: Liv0 | MetaVal2 = Liv0()

    def version(self, executable):
        stdout = self._version_from_tool(executable, "--version")
        version = stdout.splitlines()[0].strip()
        return version

    def executable(self, tool_locator: BaseTool2.ToolLocator):
        try:
            return self._delegate.executable(tool_locator)
        except ToolNotFoundException as e1:
            try:
                self._delegate = MetaVal2()
                return self._delegate.executable(tool_locator)
            except ToolNotFoundException:
                raise e1

    def program_files(self, executable):
        return self._delegate.program_files(executable)

    def name(self):
        return "LIV"

    def project_url(self):
        return "https://gitlab.com/sosy-lab/software/liv"

    def cmdline(self, executable, options, task, rlimits):
        return self._delegate.cmdline(executable, options, task, rlimits)

    def determine_result(self, run):
        return self._delegate.determine_result(run)

    def get_value_from_output(self, output, identifier):
        return self._delegate.get_value_from_output(output, identifier)
