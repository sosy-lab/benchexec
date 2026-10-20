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
    Python tasks, "CHECK( init(main()), ! uncaught(E))".
    The module passes the CPU-time and memory limits of the run to the tool,
    which decides itself how much of them it uses, and "language_version"
    from the options of the task definition, if the task definition has it.
    The last non-empty line of the output is the verdict:
    TRUE, FALSE(<exception class>) or UNKNOWN(<reason>).
    For a violated property, the exception class is the subproperty.
    """

    REQUIRED_PATHS = ["bin", "lib", "python", "VERSION"]

    _FALSE = re.compile(r"FALSE\(([A-Za-z_][A-Za-z0-9_.]*)\)")

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
        if rlimits.cputime and "--cpu-limit-seconds" not in options:
            cmd += ["--cpu-limit-seconds", str(rlimits.cputime)]
        if rlimits.memory and "--memory-limit-bytes" not in options:
            cmd += ["--memory-limit-bytes", str(rlimits.memory)]
        cmd += [task.single_input_file, "--property", task.property_file]
        if task.options is not None and "language_version" in task.options:
            language_version = task.options["language_version"]
            if not isinstance(language_version, str):
                raise UnsupportedFeatureException(
                    "language_version of the task definition must be a string"
                )
            cmd += ["--language-version", language_version]
        return cmd

    def determine_result(self, run):
        if run.exit_code:
            return result.RESULT_ERROR
        for line in reversed(run.output):
            line = line.strip()
            if not line:
                continue
            if line == "TRUE":
                return result.RESULT_TRUE_PROP
            match = self._FALSE.fullmatch(line)
            if match:
                return f"{result.RESULT_FALSE_PROP}({match.group(1)})"
            if line.startswith("UNKNOWN(") and line.endswith(")"):
                return result.RESULT_UNKNOWN
            return result.RESULT_ERROR
        return result.RESULT_ERROR
