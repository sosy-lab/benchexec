# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
# SPDX-FileCopyrightText: 2016-2020 Marek Chalupa
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.tools.template
import benchexec.result as result


class Tool(benchexec.tools.template.BaseTool2):
    """
    VeriOover
    """

    def name(self):
        return "VeriOover"

    def project_url(self):
        return "http://github.com/PaperSheeper/VeriOover-SV"

    def executable(self, tool_locator):
        return tool_locator.find_executable("VeriOover")

    def version(self, executable):
        return self._version_from_tool(executable)

    def cmdline(self, executable, options, task, rlimits):
        options = options + ["-file", task.single_input_file]
        if task.property_file:
            options = options + ["-spec", task.property_file]

        return [executable] + options

    def determine_result(self, run):
        # parse output
        status = result.RESULT_UNKNOWN
        for line in run.output:
            if "spec incorrect!" in line:
                status = result.RESULT_FALSE_PROP
            elif "spec unknown!" in line:
                status = result.RESULT_UNKNOWN
            elif "spec correct!" in line:
                status = result.RESULT_TRUE_PROP

        return status
