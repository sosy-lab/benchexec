# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.tools.template
import benchexec.result as result


class Tool(benchexec.tools.template.BaseTool2):
    """
    Tool info for SVF: a framework for static value-flow analysis.
    - Project URL: https://github.com/Lasagnenator/svf-svc-comp
    - SVF: https://github.com/SVF-tools/SVF
    """
    
    REQUIRED_PATHS = ["bin/", "z3"]

    def executable(self, tool_locator):
        return tool_locator.find_executable("svf_run.py", subdir="bin")

    def name(self):
        return "SVF"
    
    def project_url(self):
        return "https://github.com/Lasagnenator/svf-svc-comp"
    
    def version(self, executable):
        return "1"

    def cmdline(self, executable, options, task, rlimits):
        return (
            [executable]
            + [f"{f}" for f in task.input_files_or_empty]
        )

    def determine_result(self, run):
        for line in run.output:
            if result.get_result_classification(line) != result.RESULT_CLASS_OTHER:
                return line
        return result.RESULT_UNKNOWN
