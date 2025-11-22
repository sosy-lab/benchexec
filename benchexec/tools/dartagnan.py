# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.tools.template
import benchexec.result as result
from benchexec.tools.sv_benchmarks_util import (
    TaskFilesConsidered,
    handle_witness_of_task,
)


class Tool(benchexec.tools.template.BaseTool2):
    """
    Tool info for Dartagnan.
    """

    def executable(self, tool_locator):
        return tool_locator.find_executable("Dartagnan-SVCOMP.sh")

    def name(self):
        return "Dartagnan"

    def project_url(self):
        return "https://github.com/hernanponcedeleon/Dat3M"

    def cmdline(self, executable, options, task, rlimits):
        if task.property_file:
            options += [task.property_file]
        input_files, witness_options = handle_witness_of_task(
            task, options, "-witness", TaskFilesConsidered.INPUT_FILES_OR_IDENTIFIER
        )
        return [executable] + options + witness_options + input_files

    def version(self, executable):
        return self._version_from_tool(executable)

    def determine_result(self, run):
        status = result.RESULT_ERROR
        for line in run.output:
            if "unsupported property" in line:
                status = result.RESULT_ERROR
            elif "FAIL" in line:
                status = result.RESULT_FALSE_PROP
            elif "PASS" in line:
                status = result.RESULT_TRUE_PROP
            elif "integer overflow" in line:
                status = result.RESULT_FALSE_OVERFLOW
            elif "invalid dereference" in line:
                status = result.RESULT_FALSE_DEREF
            elif "user assertion" in line:
                status = result.RESULT_FALSE_REACH
            elif "data race found" in line:
                status = result.RESULT_FALSE_DATARACE
            elif "Untrackable object found" in line:
                status = result.RESULT_FALSE_MEMTRACK
            elif "Termination violation found" in line:
                status = result.RESULT_FALSE_TERMINATION
        return status

    def program_files(self, executable):
        return [executable] + self.REQUIRED_PATHS
