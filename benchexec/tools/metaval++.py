# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import logging

import benchexec.result
from benchexec.tools.sv_benchmarks_util import ILP32, LP64, get_data_model_from_task
from benchexec.tools.template import BaseTool2


class Tool(BaseTool2):
    """
    Tool info for Deductive Validator.
    """

    REQUIRED_PATHS = ["lib", "src", "metaval++.py"]

    def executable(self, tool_locator: BaseTool2.ToolLocator):
        return tool_locator.find_executable("metaval++.py")

    def program_files(self, executable):
        return [executable] + self._program_files_from_executable(
            executable, self.REQUIRED_PATHS, parent_dir=True
        )

    def version(self, executable):
        return self._version_from_tool(executable)

    def name(self):
        return "MetaVal++"

    def project_url(self):
        return "https://gitlab.com/sosy-lab/software/metavalpp"

    def cmdline(self, executable, options, task, rlimits):
        if task.property_file:
            options = options + ["--property", task.property_file]

        data_model_param = get_data_model_from_task(
            task, {ILP32: "ILP32", LP64: "LP64"}
        )

        if data_model_param and "--data-model" not in options:
            options += ["--data-model", data_model_param]

        return [executable] + options + list(task.input_files_or_identifier)

    def determine_result(self, run):
        if not run.output:
            return benchexec.result.RESULT_ERROR
        lastline = run.output[-1]
        if lastline.startswith("Witness is correct"):
            status = benchexec.result.RESULT_TRUE_PROP
        elif lastline.startswith("Witness could not be validated"):
            if ":" in lastline:
                status = benchexec.result.RESULT_ERROR + lastline.split(":")[1].strip()
            else:
                status = benchexec.result.RESULT_ERROR
        elif lastline.startswith(
            "There was an error validating the witness in the backend verifier"
        ):
            if ":" in lastline:
                status = benchexec.result.RESULT_ERROR + lastline.split(":")[1].strip()
            else:
                status = benchexec.result.RESULT_ERROR
        elif lastline.startswith("Witness file does not exist"):
            status = benchexec.result.RESULT_ERROR + "(no witness)"
        else:
            status = benchexec.result.RESULT_ERROR
        return status

    def get_value_from_output(self, output, identifier):
        # search for the text in output and get its value,
        # search the first line, that starts with the searched text
        # warn if there are more lines with the searched text
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
