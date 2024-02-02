# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0
import logging
import os
import subprocess

import benchexec.result as result
from benchexec.tools.template import ToolNotFoundException, BaseTool2


class Tool(BaseTool2):
    """
    Tool info for Coccinelle.
    Coccinelle is NOT a verification tool, but rather a tool that takes a c task and a .cocci template file
    and injects faults into the given program.
    The provided template dictates if a fault is to be injected into the program, and at which position in the code.
    """

    REQUIRED_PATHS = ["standard.h" "ocaml" "standard.iso" "ocaml"]

    def name(self):
        return "Coccinelle"

    def executable(self, tool_locator):
        return tool_locator.find_executable("spatch")
        # dir_name = os.path.dirname(exe)
        # logging.debug("Looking in %s for spatch", dir_name)
        # for _, dir_names, file_names in os.walk(dir_name):
        #     if "spatch" in file_names:
        #         return exe
        #     break

        # msg = (
        #     f"ERROR: Did find a spatch in {os.path.dirname(exe)} "
        #     f"but no 'spatch' directory besides it"
        # )
        # raise ToolNotFoundException(msg)

    def version(self, executable):
        return self._version_from_tool(executable, arg="--version", line_prefix="spatch version")

    def cmdline(self, executable, options, task, resource_limits):
        return [executable] + options + list(task.single_input_file) + [task.property_file]

    # def determine_result(self, run):
    #     if run.exit_code != 0:
    #         return result.RESULT_ERROR
    #     else:
    #         return result.RESULT_DONE

    def project_url(self):
        return "https://github.com/coccinelle/coccinelle"