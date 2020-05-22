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
import benchexec.util as util


class Tool(benchexec.tools.template.BaseTool):
    """
    Tool info for the NITWIT Validator, an interpreter-based violation witness validator.
    URL: https://github.com/moves-rwth/nitwit-validator
    """

    REQUIRED_PATHS = []
    BIN_DIR = "bin"

    def executable(self):
        executable = util.find_executable("nitwit.sh")
        bin_path = os.path.join(os.path.dirname(executable), self.BIN_DIR)
        if (
            not os.path.isdir(bin_path)
            or not os.path.isfile(os.path.join(bin_path, "nitwit32"))
            or not os.path.isfile(os.path.join(bin_path, "nitwit64"))
        ):
            logging.warning(
                "Required binary files for Nitwit not found in {0}.".format(bin_path)
            )
        return executable

    def program_files(self, executable):
        return [
            executable,
            os.path.join(self.BIN_DIR, "nitwit32"),
            os.path.join(self.BIN_DIR, "nitwit64"),
        ]

    def version(self, executable):
        return self._version_from_tool(executable, "--version")

    def name(self):
        return "Nitwit"

    def cmdline(self, executable, options, tasks, propertyfile=None, rlimits={}):
        if propertyfile:
            options = options + ["-p", propertyfile]
        return [executable] + options + tasks

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        """
        See README.md at https://github.com/moves-rwth/nitwit-validator for information
        about result codes.
        @param returncode: code returned
        @param returnsignal: signal, which terminated validator
        @param output: the std output
        @return: status of validator after executing a run
        """
        if returnsignal == 0 and (returncode == 0 or returncode == 245):
            status = result.RESULT_FALSE_REACH
        elif returncode is None or returncode in [-9, 9]:
            status = "TIMEOUT"
        elif returncode in [4, 5, 241, 242, 243, 250]:
            status = result.RESULT_UNKNOWN
        else:
            status = result.RESULT_ERROR

        if "Out of memory" in output or returncode == 251:
            status = "OUT OF MEMORY"

        if not status:
            status = result.RESULT_ERROR

        return status
