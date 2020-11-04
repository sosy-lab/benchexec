# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0


import benchexec.tools.template


class Tool(benchexec.tools.template.BaseTool2):
    """
    Fuzzing with stochastic optimization guided by CMA-ES

    Hynsung Kim, Gidon Ernst
    https://github.com/lazygrey/fuzzing_with_cmaes
    """

    REQUIRED_PATHS = [
        "fuzzer",
        "fuzzer.py",
        "cma",
        "verifiers_bytes",
        "verifiers_real",
    ]

    def executable(self, tool_locator):
        return tool_locator.find_executable("fuzzer")

    def cmdline(self, executable, options, task, rlimits):
        return [executable] + options + [task.single_input_file]

    def version(self, executable):
        return self._version_from_tool(executable)

    def name(self):
        return "CMA-ES Fuzz"

    def get_value_from_output(self, output, identifier):
        for line in reversed(output):
            if line.startswith(identifier):
                return line[len(identifier) :]
        return None
