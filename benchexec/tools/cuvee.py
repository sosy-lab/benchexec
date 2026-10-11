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
    Tool info for Cuvée, a deductive verifier that proves the property unreach-call
    of C programs without loop invariants: it summarizes loops by trace equation
    systems, whose goals it closes by rewriting with a database of lemmas,
    optionally followed by the SMT solver Z3 on the goals that remain (-fallback -z3).

    No goal left means that the property holds. A goal that simplifies to false
    means that it is violated, except with the option -unbounded, under which
    nondeterministic values range over all integers. Other goals that remain are
    not refuted, hence the result is unknown. Cuvée does not produce witnesses.
    """

    # z3 next to Cuvee.sh, which puts its own directory first on the PATH
    REQUIRED_PATHS = ["Cuvee.sh", "cuvee.jar", "z3"]

    # a goal that the simplifier refutes, printed as (goal false) or goal false,
    # or passed on to the solver, which reports it as
    # (error "goal does not hold" "Sat" "false")
    GOAL_FALSE = re.compile(r"^\(?goal false\)?$")
    SAT_FALSE = re.compile(r'"goal does not hold"\s+"Sat"\s+"false"')

    def executable(self, tool_locator):
        return tool_locator.find_executable("Cuvee.sh")

    def program_files(self, executable):
        return self._program_files_from_executable(executable, self.REQUIRED_PATHS)

    def name(self):
        return "Cuvée"

    def project_url(self):
        return "https://github.com/gernst/cuvee-plus"

    def version(self, executable):
        version = self._version_from_tool(executable, arg="-version")
        return version.replace("Cuvée", "").strip()

    def cmdline(self, executable, options, task, rlimits):
        if task.property_file and not task.property_file.endswith("unreach-call.prp"):
            raise benchexec.tools.template.UnsupportedFeatureException(
                "property not supported: " + task.property_file
            )

        arch = get_data_model_from_task(
            task, {ILP32: ["-arch", "32"], LP64: ["-arch", "64"]}
        )
        if arch is None or "-arch" in options:
            arch = []

        return [executable, *options, *arch, task.single_input_file]

    def determine_result(self, run):
        lines = list(run.output)

        # a refuted goal, since the steps before are equivalences,
        # except with -unbounded
        if "-unbounded" not in run.cmdline:
            for i, line in enumerate(lines):
                if self.GOAL_FALSE.match(line.strip()) or self.SAT_FALSE.search(
                    " ".join(lines[i : i + 3])
                ):
                    return result.RESULT_FALSE_REACH

        # errors, e.g. constructs of C that are not supported, or rewriting that
        # does not terminate, whose message is the first string at the error or on
        # the lines after it, e.g. (error "parse error" ...); goals that the solver
        # does not prove are not refuted, since the encoding for it generalizes
        for i, line in enumerate(lines):
            if line.startswith(("(error", "error", "Exception in thread")):
                message = re.search(r'"([^"]*)"', " ".join(lines[i : i + 3]))
                if message and message.group(1) == "goal does not hold":
                    return result.RESULT_UNKNOWN
                return result.RESULT_ERROR + (
                    " (" + message.group(1) + ")" if message else ""
                )

        if run.exit_code.value not in (0, None):
            return result.RESULT_ERROR

        for line in lines:
            if line.startswith(("(goal", "goal")):
                return result.RESULT_UNKNOWN

        return result.RESULT_TRUE_PROP
