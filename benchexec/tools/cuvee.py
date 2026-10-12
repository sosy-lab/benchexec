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
    Tool info for Cuvée, a deductive verifier for C programs (property unreach-call)
    and SV-LIB scripts (property correct-tags): it generates the obligations of the
    program by trace equation systems (-teq, closed by rewriting with a database of
    lemmas), by verification conditions (-vcgen), or by constrained Horn clauses
    (-chc), optionally decided by the SMT solver Z3 (-z3).

    The tool is run with -verify, which makes Cuvée decide the result itself: it
    answers correct, incorrect, or unknown to each verify-call of an SV-LIB script,
    or once to a C program, whether the program satisfies its specification. An
    incorrect answer means that the property is violated, correct answers only that
    it holds, anything else is unknown. Cuvée does not produce witnesses.
    """

    # z3 next to Cuvee.sh, which puts its own directory first on the PATH
    REQUIRED_PATHS = ["Cuvee.sh", "cuvee.jar", "z3"]

    # a goal that the simplifier refutes, printed as (goal false) or goal false;
    # a model of Z3 for a goal passed on to it, (error "goal does not hold" "Sat" ...),
    # is no counterexample, since the encoding generalizes the goal (see below)
    GOAL_FALSE = re.compile(r"^\(?goal false\)?$")

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
        if task.property_file and not task.property_file.endswith(
            ("unreach-call.prp", "correct-tags.prp", "correct-annotations.prp")
        ):
            raise benchexec.tools.template.UnsupportedFeatureException(
                "property not supported: " + task.property_file
            )

        arch = get_data_model_from_task(
            task, {ILP32: ["-arch", "32"], LP64: ["-arch", "64"]}
        )
        if arch is None or "-arch" in options:
            arch = []

        return [executable, *options, *arch, task.single_input_file]

    ANSWERS = ("correct", "incorrect", "unknown")

    # the answers of -verify: an incorrect one is a violation, also before an error, at least one answer and all of
    # them correct means that the property holds; otherwise errors, e.g. constructs that are not supported, whose
    # message is the first string at the error or on the lines after it, e.g. (error "not supported" ...)
    def determine_result(self, run):
        lines = list(run.output)
        answers = [line.strip() for line in lines if line.strip() in self.ANSWERS]

        if "incorrect" in answers:
            if run.cmdline and run.cmdline[-1].endswith(".svlib"):
                return result.RESULT_FALSE_PROP
            return result.RESULT_FALSE_REACH

        for i, line in enumerate(lines):
            if line.startswith(("(error", "error", "Exception in thread")):
                message = re.search(r'"([^"]*)"', " ".join(lines[i : i + 3]))
                return result.RESULT_ERROR + (
                    " (" + message.group(1) + ")" if message else ""
                )

        if run.exit_code.value not in (0, None) or not answers:
            return result.RESULT_ERROR

        if all(answer == "correct" for answer in answers):
            return result.RESULT_TRUE_PROP

        return result.RESULT_UNKNOWN
