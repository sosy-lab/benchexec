# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.tools.template
from benchexec import result


class Tool(benchexec.tools.template.BaseTool2):
    """
    Tool info for rIC3
    """

    def executable(self, tool_locator):
        return tool_locator.find_executable("rIC3")

    def name(self):
        return "rIC3"

    def version(self, executable):
        version_string = self._version_from_tool(executable, line_prefix="rIC3 ")
        commit_hash = self._version_from_tool(executable, line_prefix="commit_hash:")
        if commit_hash:
            # Different commits of rIC3 could have the same version number.
            # Therefore, the commit hash is appended to get a more precise version information.
            version_string += f" ({commit_hash})"
        return version_string

    def project_url(self):
        return "https://github.com/gipsyh/rIC3"

    def cmdline(self, executable, options, task, rlimits):
        # rIC3 accepts an optional positional argument for specifying certificate path,
        # which comes after the input file.
        return [executable, task.single_input_file, *options]

    def determine_result(self, run):
        for line in run.output[::-1]:
            line = line.lower().strip()
            # rIC3 has changed its output over time (each format replaces the previous one)
            # - since v1.2.0: "result: true/false"
            # - since v1.3.0: "result: safe/unsafe"
            # - since v1.5.0: "result: unsat/sat"
            # - since v1.5.2: bare "unsat/sat" without prefix
            if line.startswith("unsat"):
                return result.RESULT_TRUE_PROP
            elif line.startswith("sat"):
                return result.RESULT_FALSE_PROP
            # skip the lines that do not contain verification result
            if not line.startswith("result:"):
                continue
            res = line[len("result:") :].strip()
            if res in {"true", "safe", "unsat"}:
                return result.RESULT_TRUE_PROP
            elif res in {"false", "unsafe", "sat"}:
                return result.RESULT_FALSE_PROP
            elif res == "unknown":
                return result.RESULT_UNKNOWN
        return result.RESULT_ERROR
