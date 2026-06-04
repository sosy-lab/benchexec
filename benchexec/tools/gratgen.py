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
    GRAT-Gen converts standard DRAT unsatisfiability proofs into the GRAT format,
    enabling efficient verification by the formally verified GRATchk checker.
    """

    def executable(self, tool_locator):
        return tool_locator.find_executable("gratgen")

    def name(self):
        return "GRAT-Gen"

    def project_url(self):
        return "https://www21.in.tum.de/~lammich/grat/"

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
