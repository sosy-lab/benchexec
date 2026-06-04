# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.result as result
import benchexec.tools.template


class Tool(benchexec.tools.template.BaseTool2):
    """
    DPR-Trim checks and trims proofs in the Propagation Redundancy (PR) format and
    converts them to LPR format for checking by verified proof checkers.
    """

    def executable(self, tool_locator):
        return tool_locator.find_executable("dpr-trim")

    def name(self):
        return "DPR-Trim"

    def project_url(self):
        return "https://github.com/marijnheule/dpr-trim"

    def cmdline(self, executable, options, task, rlimits):
        return [executable, task.single_input_file, *options]

    def determine_result(self, run):
        for line in run.output:
            if line.startswith("s "):
                verdict = line.strip().split(" ")[1].strip().upper()
                try:
                    sat_arg = f"({line.strip().split(' ')[2].strip().upper()})"
                except IndexError:
                    sat_arg = ""
                if verdict == "VERIFIED":
                    return result.RESULT_TRUE_PROP + sat_arg
                elif verdict == "ERROR":
                    return result.RESULT_ERROR
        return result.RESULT_ERROR
