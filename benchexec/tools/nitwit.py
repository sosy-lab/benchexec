# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import logging
import os

import benchexec.result as result
import benchexec.tools.template
from benchexec.tools.sv_benchmarks_util import (
    get_witness_options,
    get_single_non_witness_input_file,
)


class Tool(benchexec.tools.template.BaseTool2):
    """
    Tool info for the NITWIT Validator, an interpreter-based violation witness validator.
    """

    REQUIRED_PATHS = ["bin/nitwit32", "bin/nitwit64"]
    BIN_DIR = "bin"

    def executable(self, tool_locator):
        executable = tool_locator.find_executable("nitwit.sh")
        bin_path = os.path.join(os.path.dirname(executable), self.BIN_DIR)
        if (
            not os.path.isdir(bin_path)
            or not os.path.isfile(os.path.join(bin_path, "nitwit32"))
            or not os.path.isfile(os.path.join(bin_path, "nitwit64"))
        ):
            logging.warning(
                "Required binary files for Nitwit not found in %s.", bin_path
            )
        return executable

    def version(self, executable):
        return self._version_from_tool(executable, "--version")

    def name(self):
        return "Nitwit"

    def project_url(self):
        return "https://github.com/moves-rwth/nitwit-validator"

    def cmdline(self, executable, options, task, rlimits):
        input_file = get_single_non_witness_input_file(task)
        witness_options = ["-w"]
        additional_options = get_witness_options(options, task, witness_options)

        if task.property_file:
            options = options + ["-p", task.property_file]
        return [executable] + options + additional_options + [input_file]

    def determine_result(self, run):
        """
        See README.md at https://github.com/moves-rwth/nitwit-validator for information
        about result codes.
        @return: status of validator after executing a run
        """
        if run.exit_code.value in [0, 245]:
            status = result.RESULT_FALSE_REACH
        elif run.exit_code.value in [4, 5, 241, 242, 243, 250]:
            status = result.RESULT_UNKNOWN
        else:
            status = result.RESULT_ERROR

        if ("out of memory!".lower() in (line.lower() for line in run.output)) or (
            run.exit_code.value == 251
        ):
            status = "OUT OF MEMORY"

        return status
