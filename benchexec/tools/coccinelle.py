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
    Tool info for Coccinelle
    (https://github.com/coccinelle/coccinelle).
    """

    REQUIRED_PATHS = ["standard.h" "ocaml" "standard.iso" "ocaml"]

    def name(self):
        return "Coccinelle"

    def executable(self, tool_locator):
        exe = tool_locator.find_executable("spatch")
        dir_name = os.path.dirname(exe)
        logging.debug("Looking in %s for spatch", dir_name)
        for _, dir_names, file_names in os.walk(dir_name):
            if "spatch" in file_names:
                return exe
            break
        msg = (
            f"ERROR: Did find a spatch in {os.path.dirname(exe)} "
            f"but no 'spatch' directory besides it"
        )
        raise ToolNotFoundException(msg)

    def version(self, executable):
        return self._version_from_tool(executable)

    def cmdline(self, executable, options, task, resource_limits):
        return [executable] + options + list(task.input_files) + [task.property_file]

    def program_files(self, executable):
        paths = self.REQUIRED_PATHS
        return [executable] + self._program_files_from_executable(executable, paths)

    def determine_result(self, run):
        if run.exit_code != 0:
            return result.RESULT_ERROR
        else:
            return result.RESULT_DONE

    @staticmethod
    def _version_from_tool(executable):
        version_output = subprocess.check_output(
            [executable, "--version"], universal_newlines=True
        )
        for line in version_output.splitlines():
            if line.startswith("spatch version"):
                return line.split("spatch version")[1].strip()
        return ""
