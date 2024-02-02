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
    Tool info for VFIT
    """

    REQUIRED_PATHS = []

    def name(self):
        return "V-Fit"

    def executable(self, tool_locator):
        exe = tool_locator.find_executable("vfit")
        # dir_name = os.path.dirname(exe)
        # logging.debug("Looking for V-Fit executable in %s", dir_name)
        # for _, dir_names, file_names in os.walk(dir_name):
        #     if "vfit" in file_names:
        #         return exe
        #     break
        # msg = (
        #     f"ERROR: Did find a V-Fit in {os.path.dirname(exe)} "
        #     f"but no 'vfit' directory besides it"
        # )
        # raise ToolNotFoundException(msg)
        return exe

    def version(self, executable):
        return self._version_from_tool(executable, line_prefix="v-fit version")

    def cmdline(self, executable, options, task, resource_limits):
        return [executable] + options + ["--c"] + list(task.input_files)

    # def determine_result(self, run):
    #     if run.exit_code != 0:
    #         return result.RESULT_ERROR
    #     else:
    #         return result.RESULT_DONE

    def project_url(self):
        return "https://gitlab.com/sosy-lab/software/fault-injection"
