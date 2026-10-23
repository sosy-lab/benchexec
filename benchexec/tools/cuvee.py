# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import re

import benchexec.tools.template
from benchexec import result
from benchexec.tools.sv_benchmarks_util import ILP32, LP64, get_data_model_from_task


class Tool(benchexec.tools.template.BaseTool2):
    """
    Tool info for Cuvée, a multi-language and multi-technique verification tool.
    It supports C, Dafny, Boogie, and SV-LIB among its frontends and backends.
    Verification conditions can be generated from existing annotations or inferred by automatic methods,
    including Constrained Horn Solvers and Trace Equation Systems.
    """

    REQUIRED_PATHS = ["cuvee.jar", "z3"]

    def executable(self, tool_locator):
        return tool_locator.find_executable("Cuvee.sh")

    def name(self):
        return "Cuvée"

    def project_url(self):
        return "https://github.com/gernst/cuvee-plus"

    def version(self, executable):
        return self._version_from_tool(executable, arg="-version", line_prefix="Cuvée")

    def cmdline(self, executable, options, task, rlimits):
        arch = get_data_model_from_task(
            task, {ILP32: ["-arch", "32"], LP64: ["-arch", "64"]}
        )
        if arch is None or "-arch" in options:
            arch = []

        return [executable, *options, *arch, task.single_input_file]

    # the answers of Cuvée, one for each goal and lemma, e.g. of the procedures (-teq, -vcgen), or one for the whole
    # program (-chc): correct means that it holds, incorrect that it does not, i.e., that the property is violated;
    # an incorrect one decides, also before an error, and all of them must be correct for the property to hold;
    # errors, e.g. constructs that are not supported, are reported with the first string at the error or on the lines
    # after it, e.g. (error "not supported" ...)
    def determine_result(self, run):
        answers = {
            line for line in run.output if line in ("correct", "incorrect", "unknown")
        }

        if "incorrect" in answers:
            return result.RESULT_FALSE_PROP

        for i, line in enumerate(run.output):
            if line.startswith(("(error", "error", "Exception in thread")):
                message = re.search(r'"([^"]*)"', " ".join(run.output[i : i + 3]))
                return result.RESULT_ERROR + (
                    " (" + message.group(1) + ")" if message else ""
                )

        if run.exit_code.value or not answers:
            return result.RESULT_ERROR

        if answers == {"correct"}:
            return result.RESULT_TRUE_PROP

        return result.RESULT_UNKNOWN
