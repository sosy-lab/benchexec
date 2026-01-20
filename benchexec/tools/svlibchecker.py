# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2024 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0
import logging

import benchexec.tools.template
from benchexec.tools.sv_benchmarks_util import (
    handle_witness_of_task,
    TaskFilesConsidered,
)
import benchexec.result as result


class Tool(benchexec.tools.template.BaseTool2):
    """
    Tool info module for the tool PySvLib which is an extensible
    framework for prototyping and experimenting with model checking
    techniques for [SV-LIB](https://gitlab.com/sosy-lab/benchmarking/sv-lib)
    programs.
    """

    REQUIRED_PATHS = []

    def executable(self, tool_locator):
        return tool_locator.find_executable("svlibchecker.py")

    def name(self):
        return "SvLibChecker"

    def project_url(self):
        return "https://gitlab.com/sosy-lab/software/svlibchecker"

    def version(self, executable):
        version_string = self._version_from_tool(executable)
        return version_string

    def cmdline(self, executable, options, task, rlimits):
        input_files, mapping_options = handle_witness_of_task(
            task, options, "--witness", TaskFilesConsidered.INPUT_FILES
        )

        return [executable, *options, *mapping_options, *input_files]

    def get_value_from_output(self, output, identifier):
        # search for the text in output and get its value,
        # search the first line, that starts with the searched text
        # warn if there are more lines
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

    def determine_result(self, run):
        verification_result_identifier = "Verification result:"
        for line in reversed(run.output):
            if line.startswith(verification_result_identifier):
                line = line[len(verification_result_identifier) :].strip()
                if "correct" == line:
                    return result.RESULT_TRUE_PROP
                elif "incorrect" == line:
                    return result.RESULT_FALSE_PROP
                elif "unknown" == line:
                    return result.RESULT_UNKNOWN
                else:
                    logging.warning("unrecognized verification result: '%s'", line)
            elif line.startswith("Error:"):
                return result.RESULT_ERROR + " (" + line[len("Error:") :].strip() + ")"

        # if no result was found, return error
        return result.RESULT_ERROR
