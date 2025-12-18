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
    Tool info module for the tool PySvLib which is a python package
    for working with [SV-LIB](https://gitlab.com/sosy-lab/benchmarking/sv-lib)
    programs. This allows one to call the CLI tools provided by PySvLib
    via BenchExec.
    """

    REQUIRED_PATHS = []

    def executable(self, tool_locator):
        return tool_locator.find_executable("pysvlib_cli.py", subdir="pysvlib")

    def name(self):
        return "PySvLib"

    def project_url(self):
        return "https://gitlab.com/sosy-lab/benchmarking/sv-lib"

    def version(self, executable):
        version_string = self._version_from_tool(executable)
        return version_string

    def cmdline(self, executable, options, task, rlimits):
        input_files, mapping_options = handle_witness_of_task(
            task, options, "--witness", TaskFilesConsidered.INPUT_FILES_OR_IDENTIFIER
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
        """
        @return: status of PySvLib after executing a run
        """
        for line in reversed(run.output):
            if "correct" == line:
                return result.RESULT_TRUE_PROP
            elif "incorrect" == line:
                return result.RESULT_FALSE_PROP

        # We could not find a definitive result in the output
        if run.exit_code.value == 0:
            return result.RESULT_DONE
        else:
            return result.RESULT_ERROR
