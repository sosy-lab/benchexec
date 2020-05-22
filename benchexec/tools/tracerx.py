# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.result as result
import benchexec.util as util
import benchexec.tools.template
import benchexec.model


class Tool(benchexec.tools.template.BaseTool):
    """
    Tool info for Tracer-X (https://www.comp.nus.edu.sg/~tracerx/).
    """

    REQUIRED_PATHS = [
        "bin",
        "include",
        "libraries",
        "llvm-3.4.2",
        "tracerx_build",
    ]

    def executable(self):
        return util.find_executable("bin/tracerx")

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

    def cmdline(self, executable, options, tasks, propertyfile=None, rlimits={}):
        if propertyfile:
            options += ["--property-file=" + propertyfile]
        if benchexec.model.MEMLIMIT in rlimits:
            options += ["--max-memory=" + str(rlimits[benchexec.model.MEMLIMIT])]
        if benchexec.model.TIMELIMIT in rlimits:
            options += ["--max-time=" + str(rlimits[benchexec.model.TIMELIMIT])]
        if benchexec.model.WALLTIMELIMIT in rlimits:
            options += ["--max-walltime=" + str(rlimits[benchexec.model.WALLTIMELIMIT])]
        if benchexec.model.SOFTTIMELIMIT in rlimits:
            options += [
                "--max-cputime-soft=" + str(rlimits[benchexec.model.SOFTTIMELIMIT])
            ]
        if benchexec.model.HARDTIMELIMIT in rlimits:
            options += [
                "--max-cputime-hard=" + str(rlimits[benchexec.model.HARDTIMELIMIT])
            ]

        return [executable] + options + tasks

    def name(self):
        return "Tracer-X"

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        """
        Parse the output of the tool and extract the verification result.
        This method always needs to be overridden.
        If the tool gave a result, this method needs to return one of the
        benchexec.result.RESULT_* strings.
        Otherwise an arbitrary string can be returned that will be shown to the user
        and should give some indication of the failure reason
        (e.g., "CRASH", "OUT_OF_MEMORY", etc.).
        """
        for line in output:
            if line.startswith("KLEE: ERROR: "):
                if "ASSERTION FAIL:" in line:
                    return result.RESULT_FALSE_REACH
                elif "memory error: out of bound pointer" in line:
                    return result.RESULT_FALSE_DEREF
                elif "overflow" in line:
                    return result.RESULT_FALSE_OVERFLOW
                else:
                    return "ERROR ({0})".format(returncode)
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
