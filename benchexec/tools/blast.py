# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import os

import benchexec.util as util
import benchexec.tools.template
import benchexec.result as result


class Tool(benchexec.tools.template.BaseTool):
    REQUIRED_PATHS = ["etv", "bin"]

    def blast_exe(self):
        return "pblast.opt"

    def executable(self):
        return util.find_executable("svcomprunner", "bin/svcomprunner")

    def program_files(self, executable):
        return self._program_files_from_executable(
            executable, self.REQUIRED_PATHS, parent_dir=True
        )

    def version(self, executable):
        return self._version_from_tool(
            os.path.join(os.path.dirname(executable), self.blast_exe())
        )[6:11]

    def cmdline(self, executable, options, tasks, propertyfile, rlimits):
        spec = ["-propertyfile", propertyfile] if propertyfile is not None else []
        return [executable] + ["ocamltune", self.blast_exe()] + options + spec + tasks

    def name(self):
        return "BLAST"

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        status = result.RESULT_UNKNOWN
        for line in output:
            if line.startswith("Error found! The system is unsafe :-("):
                status = result.RESULT_FALSE_REACH
            elif line.startswith("No error found.  The system is safe :-)"):
                status = result.RESULT_TRUE_PROP
            elif line.startswith("Fatal error: exception Out_of_memory"):
                status = "OUT OF MEMORY"
            elif line.startswith("Error: label 'ERROR' appears multiple times"):
                status = "ERROR"
            elif returnsignal == 9:
                status = result.RESULT_TIMEOUT
            elif "Ack! The gremlins again!" in line:
                status = "EXCEPTION (Gremlins)"
        return status
