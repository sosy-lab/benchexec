# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.tools.template
from benchexec.tools.sv_benchmarks_util import get_data_model_from_task, ILP32, LP64


class Tool(benchexec.tools.template.BaseTool2):
    """
    Tool info for Legion.
    """

    REQUIRED_PATHS = [
        "legion-sv",
        "Legion.py",
        "__VERIFIER.c",
        "__VERIFIER32.c",
        "__VERIFIER_assume.c",
        "__VERIFIER_assume.instr.s",
        "__trace_jump.s",
        "__trace_buffered.c",
        "tracejump.py",
        "lib",
    ]

    def executable(self, tool_locator):
        return tool_locator.find_executable("legion-sv")

    def version(self, executable):
        return self._version_from_tool(executable, ignore_stderr=True)

    def name(self):
        return "Legion"

    def project_url(self):
        return "https://github.com/Alan32Liu/Legion"

    def cmdline(self, executable, options, task, rlimits):
        data_model_param = get_data_model_from_task(task, {ILP32: "-32", LP64: "-64"})
        if data_model_param and data_model_param not in options:
            options += [data_model_param]

        return [executable, *options, *task.input_files_or_identifier]
