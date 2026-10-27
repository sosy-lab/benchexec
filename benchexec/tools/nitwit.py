# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import logging
import os

import benchexec.tools.template
from benchexec import result
from benchexec.tools.sv_benchmarks_util import (
    ILP32,
    LP64,
    TaskFilesConsidered,
    get_data_model_from_task,
    handle_witness_of_task,
)


class Tool(benchexec.tools.template.BaseTool2):
    """
    Tool info for the NITWIT Validator, an interpreter-based validator that confirms
    violation witnesses and refutes correctness witnesses: it runs the program, and a
    run that calls the error function shows that the program violates the property.
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
        input_file, witness_options = handle_witness_of_task(
            task,
            options,
            "-w",
            TaskFilesConsidered.SINGLE_INPUT_FILE,
        )

        if task.property_file:
            options = options + ["-p", task.property_file]

        data_model_param = get_data_model_from_task(task, {ILP32: "-32", LP64: "-64"})
        if data_model_param and data_model_param not in options:
            options = options + [data_model_param]

        return [executable] + options + witness_options + input_file

    def determine_result(self, run):
        """
        See docs/exit-codes.md at https://github.com/moves-rwth/nitwit-validator for
        information about result codes: 0 (and 245 of NITWIT 3) confirm a violation
        witness, 253 refutes a correctness witness by a run that calls the error
        function.
        @return: status of validator after executing a run
        """
        if run.exit_code.value in [0, 245, 253]:
            status = result.RESULT_FALSE_REACH
        elif run.exit_code.value in [4, 5, 241, 242, 243, 250, 252]:
            status = result.RESULT_UNKNOWN
        else:
            status = result.RESULT_ERROR

        if ("out of memory!".lower() in (line.lower() for line in run.output)) or (
            run.exit_code.value == 251
        ):
            status = "OUT OF MEMORY"

        return status
