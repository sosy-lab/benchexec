# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
# SPDX-FileCopyrightText: 2016-2020 Marek Chalupa
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.result as result
from benchexec.tools.template import ToolNotFoundException

from .symbiotic4 import Tool as OldSymbiotic


class Tool(OldSymbiotic):
    """
    Symbiotic tool info object
    """

    def executable(self, tool_locator):
        """
        Find the path to the executable file that will get executed.
        This method always needs to be overridden,
        and most implementations will look similar to this one.
        The path returned should be relative to the current directory.
        """
        try:
            executable = tool_locator.find_executable("symbiotic", subdir="bin")
        except ToolNotFoundException:
            # this may be the old version of Symbiotic
            executable = OldSymbiotic.executable(self, tool_locator)

        self._version = self.version(executable)
        return executable

    def program_files(self, executable):
        paths = self.REQUIRED_PATHS
        return [executable] + self._program_files_from_executable(
            executable, paths, parent_dir=True
        )

    def _version_newer_than(self, vers):
        """
        Determine whether the version is greater than some given version
        """
        vers_num = self._version[: self._version.index("-")]
        if not vers_num[0].isdigit():
            # this is the old version which is "older" than any given version
            return False

        v1 = list(map(int, vers_num.split(".")))
        v2 = list(map(int, vers.split(".")))
        assert len(v1) == 3
        assert len(v2) == 3

        if v1[0] > v2[0]:
            return True
        elif v1[0] == v2[0]:
            if v1[1] == v2[1]:
                return v1[2] >= v2[2]
            elif v1[1] > v2[1]:
                return True

        return False

    def _getPhase(self, output):
        lastphase = "before-instr"
        for line in output:
            if line.startswith("INFO: Starting instrumentation"):
                lastphase = "instrumentation"
            elif line.startswith("INFO: Instrumentation time"):
                lastphase = "instr-finished"
            elif line.startswith("INFO: Starting slicing"):
                lastphase = "slicing"
            elif line.startswith("INFO: Total slicing time"):
                lastphase = "slicing-finished"
            elif line.startswith("INFO: Starting verification"):
                lastphase = "verification"
            elif line.startswith("INFO: Verification time"):
                lastphase = "verification-finished"
            elif line.startswith("INFO: Replaying error path"):
                lastphase = "cex-confirmation"
            elif line.startswith("INFO: Replaying error path time"):
                lastphase = "cex-confirmation-finished"

        return lastphase

    def determine_result(self, run):
        if not run.output:
            return f"{result.RESULT_ERROR}(no output)"

        if self._version_newer_than("4.0.1"):
            for line in run.output:
                line = line.strip()
                if line == "RESULT: true":
                    return result.RESULT_TRUE_PROP
                elif line == "RESULT: unknown":
                    return result.RESULT_UNKNOWN
                elif line == "RESULT: done":
                    return result.RESULT_DONE
                elif line.startswith("RESULT: false(valid-deref)"):
                    return result.RESULT_FALSE_DEREF
                elif line.startswith("RESULT: false(valid-free)"):
                    return result.RESULT_FALSE_FREE
                elif line.startswith("RESULT: false(valid-memtrack)"):
                    return result.RESULT_FALSE_MEMTRACK
                elif line.startswith("RESULT: false(valid-memcleanup)"):
                    return result.RESULT_FALSE_MEMCLEANUP
                elif line.startswith("RESULT: false(no-overflow)"):
                    return result.RESULT_FALSE_OVERFLOW
                elif line.startswith("RESULT: false(termination)"):
                    return result.RESULT_FALSE_TERMINATION
                elif line.startswith("RESULT: false"):
                    return result.RESULT_FALSE_REACH
        else:
            # old version of Symbiotic
            return OldSymbiotic.determine_result(self, run)

        if run.was_timeout:
            return self._getPhase(run.output)  # generates TIMEOUT(phase)
        elif run.exit_code.signal:
            return (
                f"KILLED (signal {run.exit_code.signal}, {self._getPhase(run.output)})"
            )
        elif run.exit_code.value != 0:
            return (
                f"{result.RESULT_ERROR}"
                f"(returned {run.exit_code.value}, {self._getPhase(run.output)})"
            )

        return f"{result.RESULT_ERROR}(unknown, {self._getPhase(run.output)})"
