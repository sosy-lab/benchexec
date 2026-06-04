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
    VeriPB is a proof checker for the pseudo-Boolean proof format, a strictly more
    expressive generalization of DRAT that can certify advanced reasoning techniques
    such as symmetry breaking, XOR reasoning, and dominance breaking.
    """

    def executable(self, tool_locator):
        return tool_locator.find_executable("veripb_bin_static")

    def name(self):
        return "VeriPB"

    def project_url(self):
        return "https://www.bartbogaerts.eu/talks/veripb-tutorial-series/"

    def cmdline(self, executable, options, task, rlimits):
        if task.property_file is None:
            raise benchexec.tools.template.UnsupportedFeatureException(
                "VeriPB requires a certificate (proof file) as the property file."
            )
        return [executable, *options, task.single_input_file, task.property_file]

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
