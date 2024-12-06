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
    Tool info for MoXI-MC-Flow
    """

    REQUIRED_PATHS = [
        "deps/",
        "src/",
        "json-schema/",
        "sortcheck.py",
        "translate.py",
    ]

    def executable(self, tool_locator):
        return tool_locator.find_executable("modelcheck.py")

    def name(self):
        return "MoXI-MC-Flow"

    def project_url(self):
        return "https://github.com/ModelChecker/moxi-mc-flow"

    def cmdline(self, executable, options, task, rlimits):
        if rlimits.cputime and "--timeout" not in options:
            # The `--timeout` parameter must be passed to the tool
            # to prevent it from using its default value,
            # which could be shorter than the limit set by BenchExec
            # and cause early termination.
            # Moreover, in practice the tool sometimes terminates itself prematurely
            # even when the exact time limit is passed.
            # To prevent this and ensure the tool utilizes the full time limit,
            # a factor of 2 is applied to the timeout value.
            options += ["--timeout", str(rlimits.cputime * 2)]
        return ["python3", executable, task.single_input_file, *options]

    def determine_result(self, run):
        """
        @return: verification result obtained from MoXI-MC-Flow
        """
        for line in run.output[::-1]:
            if line.startswith("unsat"):
                return result.RESULT_TRUE_PROP
            if line.startswith("sat"):
                return result.RESULT_FALSE_PROP
        return result.RESULT_ERROR
