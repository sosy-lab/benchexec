# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2024 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

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

    def determine_result(self, run):
        """
        @return: status of PySvLib after executing a run
        """

        status = None

        for line in reversed(run.output):
            if "correct" == line:
                status = result.RESULT_TRUE_PROP
                break
            elif "incorrect" == line:
                status = result.RESULT_FALSE_REACH
                break

        if not status:
            if run.returncode == 0:
                status = result.RESULT_DONE
            else:
                status = result.RESULT_ERROR
        return status
