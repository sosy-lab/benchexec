# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.result as result
import benchexec.tools.template
import benchexec.model
from benchexec.tools.sv_benchmarks_util import get_data_model_from_task, ILP32, LP64


class Tool(benchexec.tools.template.BaseTool2):
    """
    Tool info for Tracer-X.
    """

    def executable(self, tool_locator):
        return tool_locator.find_executable("tracerx", subdir="bin")

    def program_files(self, executable):
        return self._program_files_from_executable(
            executable, self.REQUIRED_PATHS, parent_dir=True
        )

    def version(self, executable):
        """
        The output looks like this:
        Tracer-X 0.2.0 (https://www.comp.nus.edu.sg/~tracerx/)
          Built August 19 2019
          Build mode: Release
          Build revision: 60794e3eac58744548657500e425241b57f4bdb7
        LLVM (http://llvm.org/):
          LLVM version 3.4.2
          Optimized build.
          Built Oct 15 2014 (13:57:47).
          Default target: x86_64-pc-linux-gnu
          Host CPU: bdver1
        """
        version = self._version_from_tool(executable, line_prefix="KLEE")
        return version.split("(")[0].strip()

    def cmdline(self, executable, options, task, rlimits):
        if task.property_file:
            options += [f"--property-file={task.property_file}"]
        if rlimits.memory:
            options += [f"--max-memory={rlimits.memory}"]
        if rlimits.cputime:
            options += [f"--max-cputime-soft={rlimits.cputime}"]

        data_model_param = get_data_model_from_task(task, {ILP32: "--32", LP64: "--64"})
        if data_model_param and data_model_param not in options:
            options += [data_model_param]

        return [executable] + options + list(task.input_files_or_identifier)

    def name(self):
        return "Tracer-X"

    def project_url(self):
        return "https://www.comp.nus.edu.sg/~tracerx/"

    def determine_result(self, run):
        """
        Parse the output of the tool and extract the verification result.
        This method always needs to be overridden.
        If the tool gave a result, this method needs to return one of the
        benchexec.result.RESULT_* strings.
        Otherwise an arbitrary string can be returned that will be shown to the user
        and should give some indication of the failure reason
        (e.g., "CRASH", "OUT_OF_MEMORY", etc.).
        """
        for line in run.output:
            if line.startswith("KLEE: ERROR: "):
                if "ASSERTION FAIL:" in line:
                    return result.RESULT_FALSE_REACH
                elif "memory error: out of bound pointer" in line:
                    return result.RESULT_FALSE_DEREF
                elif "overflow" in line:
                    return result.RESULT_FALSE_OVERFLOW
                else:
                    return f"ERROR ({run.exit_code.value})"
            if line.startswith("KLEE: done"):
                return result.RESULT_DONE
        return result.RESULT_UNKNOWN

    def get_value_from_output(self, lines, identifier):
        # search for the text in output and get its value,
        # stop after the first line, that contains the searched text
        for line in lines:
            if line.startswith("KLEE: done: ") and line.find(identifier + " = ") != -1:
                splittedLine = line.split(" = ")
                return splittedLine[1].strip()
        return None
