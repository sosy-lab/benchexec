# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2026 The Board of Trustees of the University of Iowa
#
# SPDX-License-Identifier: Apache-2.0

import os
import re

import benchexec.tools.template
from benchexec import result


class Tool(benchexec.tools.template.BaseTool2):
    """
    Tool info for kMoXI, a model checker for MoXI built on Kind 2
    (https://github.com/kind2-mc/kind2).

    The archive of kMoXI holds the executable bin/kmoxi and the SMT solvers
    it runs, in bin/ as well; their paths are given on the command line.
    kMoXI answers each query of a check-system command with sat, unsat or
    unknown, in a check-system response, as the :result attribute of the
    query.
    """

    REQUIRED_PATHS = ["bin/", "licenses/", "LICENSE", "README"]

    # The solvers kMoXI can be given, by the name of their executable in the
    # archive and the option that gives kMoXI their path
    SOLVERS = [
        ("z3", "--z3_bin"),
        ("bitwuzla", "--bitwuzla_bin"),
        ("mathsat", "--mathsat_bin"),
    ]

    def executable(self, tool_locator):
        return tool_locator.find_executable("kmoxi", subdir="bin")

    def name(self):
        return "kMoXI"

    def project_url(self):
        return "https://github.com/kind2-mc/kind2"

    def version(self, executable):
        # The first line is "kMoXI v<version> (Kind 2 <version>)"
        return self._version_from_tool(executable, line_prefix="kMoXI v")

    def program_files(self, executable):
        return [executable] + self._program_files_from_executable(
            executable, self.REQUIRED_PATHS, parent_dir=True
        )

    def cmdline(self, executable, options, task, rlimits):
        solvers = []
        bin_dir = os.path.dirname(executable)
        for name, option in self.SOLVERS:
            path = os.path.join(bin_dir, name)
            if option not in options and os.path.isfile(path):
                solvers += [option, path]
        return [
            executable,
            "--color",
            "false",
            *solvers,
            *options,
            task.single_input_file,
        ]

    def determine_result(self, run):
        """
        The answers of kMoXI to the queries of the model, from lines such as
        ` :query (q :result unsat :certificate q_cert)`. The model of a task
        has one query: the property holds if its reachability condition
        cannot be reached (unsat), and is violated if it can (sat). The result
        is unknown only if kMoXI answers unknown, and an error otherwise: an
        SMT-LIB error response, with its message, or no answer at all.
        """
        answers = set()
        for line in run.output:
            line = line.strip()
            match = re.match(
                r":query \((\|[^|]*\||\S+) :result (sat|unsat|unknown)\b", line
            )
            if match:
                answers.add(match.group(2))
            elif line.startswith("(error "):
                # Every error of kMoXI, such as a syntax or sort error in the
                # model, is an SMT-LIB error response
                message = line[len("(error ") : -1].strip('"')
                return f"{result.RESULT_ERROR} ({message})"

        if "sat" in answers:
            return result.RESULT_FALSE_PROP
        if answers == {"unsat"}:
            return result.RESULT_TRUE_PROP
        if answers == {"unknown"}:
            # kMoXI gave up
            return result.RESULT_UNKNOWN
        # No answer, as after a crash, or none that is recognized
        return result.RESULT_ERROR
