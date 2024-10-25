# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import logging
import re

import benchexec.result
from benchexec.tools.sv_benchmarks_util import ILP32, LP64, get_data_model_from_task
from benchexec.tools.template import BaseTool2


class Tool(BaseTool2):
    """
    Tool info for Deductive Validator.
    """

    REQUIRED_PATHS = ["lib", "src"]

    def executable(self, tool_locator: BaseTool2.ToolLocator):
        return tool_locator.find_executable("metaval++.py")

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

        return [executable] + options + list(task.single_input_file)

    @staticmethod
    def substring_after_identifier(string, identifier, occurrences=1):
        return (
            identifier.join(string.split(identifier)[occurrences:])
            if occurrences > 0
            else string
        )

    def determine_result(self, run):
        if not run.output:
            return benchexec.result.RESULT_ERROR
        lastline = run.output[-1]
        if lastline.startswith("Witness is correct"):
            return benchexec.result.RESULT_TRUE_PROP
        elif lastline.startswith("Witness could not be validated"):
            if ":" in lastline:
                return (
                    benchexec.result.RESULT_ERROR
                    + self.substring_after_identifier(lastline, ":").strip()
                )
            else:
                return benchexec.result.RESULT_ERROR
        elif lastline.startswith(
            "There was an error validating the witness in the backend verifier"
        ):
            if ":" in lastline:
                return (
                    benchexec.result.RESULT_ERROR
                    + self.substring_after_identifier(lastline, ":").strip()
                )
            else:
                return benchexec.result.RESULT_ERROR
        elif lastline.startswith("Witness file does not exist"):
            return benchexec.result.RESULT_ERROR + "(no witness)"
        else:
            return benchexec.result.RESULT_ERROR

    def get_value_from_output(self, output, identifier):
        # Search the text line per line using the regex passed as identifier
        # and return the first match found. If the regex has groups,
        # only the first group will be returned.
        match = None
        for line in output:
            matches = re.findall(identifier, line)
            if matches:
                if isinstance(matches[0], tuple):
                    logging.warning(
                        "The regex '%s' has groups, but only the first group will be returned",
                        identifier,
                    )
                    match = matches[0][0]
                else:
                    match = matches[0]
                break
        return match
