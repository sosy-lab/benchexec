# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.result as result
from benchexec.tools.template import BaseTool2


class Tool(BaseTool2):
    """
    Tool info module for SWAT, a dynamic symbolic execution tool for Java 17.
    SWAT is currently being developed by the Institute for IT Security at the University of Luebeck.
    """

    REQUIRED_PATHS = [
        "knife-fuzzer",
        "local_z3_installation",
        "WitnessCreator",
        "run-swat.sh",
        "run_swat.py",
    ]

    def executable(self, tool_locator):
        return tool_locator.find_executable("run-swat.sh")

    def name(self):
        return "SWAT"

    def project_url(self):
        return "https://www.its.uni-luebeck.de/en/research/tools/swat/"

    def version(self, executable):
        return self._version_from_tool(executable, arg="-v")

    def cmdline(self, executable, options, task, rlimits):
        cmd = [executable] + options
        if task.property_file:
            cmd.append(task.property_file)
        return cmd + list(task.input_files)

    def determine_result(self, run):
        if run.output.any_line_contains("== ERROR-UNREACH-CALL"):
            return result.RESULT_FALSE_REACH
        elif run.output.any_line_contains("== ERROR"):
            return result.RESULT_FALSE_PROP
        elif run.output.any_line_contains("== OK"):
            return result.RESULT_TRUE_PROP
        elif run.output.any_line_contains("== DONT-KNOW"):
            return result.RESULT_UNKNOWN

        return result.RESULT_ERROR
