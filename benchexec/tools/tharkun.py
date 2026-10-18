# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2026 CISPA Helmholtz Center for Information Security
#
# SPDX-License-Identifier: Apache-2.0

import re

import benchexec.tools.template
from benchexec import result
from benchexec.tools.template import UnsupportedFeatureException


class Tool(benchexec.tools.template.BaseTool2):
    """
    Tool info for Tharkun, a verifier for Python programs.

    Tharkun decides the uncaught-exception properties of the SV-Benchmarks
    Python tasks, "CHECK( init(main()), ! uncaught(E))". Its last line of output
    is the verdict: TRUE, FALSE(<exception class>), UNKNOWN(<reason>)
    or ERROR(<reason>).

    The tool-info module requires a property file and exactly one input file.
    It adds the following parameters to the command line:
    --budget-seconds with 90% of the CPU-time limit, if there is one;
    --run-memory-mb with 60% of the memory limit, if there is one;
    --language-version with the value of "language_version" in the options
    of the task definition, or 3.14 if the task definition has none.
    It requests no witness. For a violated property, the result is
    "false(<exception class>)": the exception class is the subproperty.
    A run that was terminated, that ended with a non-zero exit code, or whose
    output is not of the expected form is an error and never a verdict.
    """

    REQUIRED_PATHS = ["bin", "lib", "python", "VERSION"]

    # Share of the CPU-time limit after which the tool stops searching
    # and reports what it has, such that the verdict is printed in time.
    BUDGET_SHARE = 0.9
    # Share of the memory limit that the runs of the program under verification
    # may use together. A run that exceeds it ends; the verifier itself continues.
    RUN_MEMORY_SHARE = 0.6

    DEFAULT_LANGUAGE_VERSION = "3.14"

    # The whole line of a verdict.
    _VERDICT = re.compile(r"(TRUE|FALSE|UNKNOWN|ERROR)(?:\((.*)\))?", re.IGNORECASE)
    # A verdict word anywhere in a line.
    _VERDICT_TOKEN = re.compile(r"\b(?:TRUE|FALSE|UNKNOWN|ERROR)\b", re.IGNORECASE)
    # Log lines of the tool that may contain a verdict word:
    # the intermediate results of its stages, the witness it prints, the first line
    # ("tharkun-sv <version>: <program> ! uncaught(<classes>)", which holds the path
    # of the program) and the summary line ("tharkun-sv: <n> runs in <s>s; <reason>",
    # which repeats the reason of an "unknown" verdict).
    _LOG_LINE = re.compile(
        r"tharkun-sv [0-9]+(?:\.[0-9]+)*: .* ! uncaught\([^()]*\)$|"
        r"tharkun-sv: (?:"
        r"symbolic:product: |"
        r"(?!(?i:true|false|unknown|error): )(?!(?i:false)\()[A-Za-z][A-Za-z0-9_ -]*: |"
        r"[0-9]+ runs in [0-9]+(?:\.[0-9]+)?s; |"
        r"witness \{"
        r")"
    )

    def executable(self, tool_locator):
        return tool_locator.find_executable("tharkun", subdir="bin")

    def program_files(self, executable):
        return self._program_files_from_executable(
            executable, self.REQUIRED_PATHS, parent_dir=True
        )

    def version(self, executable):
        return self._version_from_tool(executable)

    def name(self):
        return "Tharkun"

    def project_url(self):
        return "https://github.com/ardier/tharkun"

    def cmdline(self, executable, options, task, rlimits):
        if not task.property_file:
            raise UnsupportedFeatureException(f"{self.name()} requires a property file")

        cmd = [executable, *options]
        if rlimits.cputime:
            budget = max(5, int(rlimits.cputime * self.BUDGET_SHARE))
            cmd += ["--budget-seconds", str(budget)]
        if rlimits.memory:
            run_memory = max(64, int(rlimits.memory * self.RUN_MEMORY_SHARE) // 2**20)
            cmd += ["--run-memory-mb", str(run_memory)]
        cmd += [task.single_input_file, "--property", task.property_file]
        cmd += ["--language-version", self._language_version(task)]
        return cmd

    def _language_version(self, task):
        """
        Return the language version that the task definition declares
        in "options: language_version", which has to be a string.
        A task without this declaration is written in Python 3.14.
        """
        if task.options is None:
            return self.DEFAULT_LANGUAGE_VERSION
        if not isinstance(task.options, dict):
            raise UnsupportedFeatureException(
                "the options of the task definition must be a mapping"
            )
        version = task.options.get("language_version", self.DEFAULT_LANGUAGE_VERSION)
        if type(version) is not str or not version.strip():
            raise UnsupportedFeatureException(
                "language_version of the task definition must be a non-empty string"
            )
        return version

    def determine_result(self, run):
        if run.was_timeout:
            return result.RESULT_TIMEOUT
        exit_code = run.exit_code
        if exit_code is not None and exit_code.signal:
            return f"{result.RESULT_ERROR} (signal {exit_code.signal})"
        if exit_code is not None and exit_code.value:
            return f"{result.RESULT_ERROR} (exit status {exit_code.value})"
        if run.was_terminated:
            return f"{result.RESULT_ERROR} ({run.termination_reason})"

        try:
            kind, argument = self._parse_verdict(run.output)
        except ValueError as e:
            # Output that is not understood is never a verdict.
            return f"{result.RESULT_ERROR} ({e})"

        if kind == "TRUE":
            return result.RESULT_TRUE_PROP
        if kind == "FALSE":
            # The subproperty is the class of the uncaught exception.
            if argument:
                return f"{result.RESULT_FALSE_PROP}({argument})"
            return result.RESULT_FALSE_PROP
        if kind == "UNKNOWN":
            return result.RESULT_UNKNOWN
        if argument:
            return f"{result.RESULT_ERROR} ({argument})"
        return result.RESULT_ERROR

    def _parse_verdict(self, output):
        """
        Find the verdict in the output of the tool.
        The output has to contain exactly one verdict line, as its last
        non-empty line, and no verdict word outside of the log lines of the tool.
        @return a pair of the verdict in upper case and its argument
            (the exception class or the reason), which is None if there is none
        @raise ValueError: if the output does not have this form
        """
        verdicts = []
        last_line = ""
        for line in "\n".join(output).splitlines():
            line = line.strip()
            if line:
                last_line = line
            match = self._VERDICT.fullmatch(line)
            if match:
                kind, argument = match.group(1).upper(), match.group(2)
                depth = 0
                for char in argument or "":
                    if char == "(":
                        depth += 1
                    elif char == ")":
                        depth -= 1
                        if depth < 0:
                            raise ValueError("text after verdict closing parenthesis")
                if depth:
                    raise ValueError("unbalanced verdict reason")
                if kind == "TRUE" and argument is not None:
                    raise ValueError("TRUE verdict cannot have a reason")
                verdicts.append((kind, argument))
            elif self._VERDICT_TOKEN.search(line) and not self._LOG_LINE.match(line):
                raise ValueError("malformed or embedded verdict token")
        if len(verdicts) != 1:
            raise ValueError(f"expected one verdict, found {len(verdicts)}")
        if not self._VERDICT.fullmatch(last_line):
            raise ValueError("verdict is not the final nonempty line")
        return verdicts[0]
