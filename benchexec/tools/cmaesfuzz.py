# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0


import re
import benchexec.util as util
import benchexec.tools.template


class Tool(benchexec.tools.template.BaseTool):
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

    def executable(self):
        return util.find_executable("fuzzer")

    def version(self, executable):
        return self._version_from_tool(executable)

    def name(self):
        return "CMA-ES Fuzz"

    def get_value_from_output(self, lines, identifier):
        for line in reversed(lines):
            pattern = identifier
            if pattern[-1] != ":":
                pattern += ":"
            match = re.match("^" + pattern + "([^(]*)", line)
            if match and match.group(1):
                return match.group(1).strip()
        return None
