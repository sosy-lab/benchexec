# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
# SPDX-FileCopyrightText: 2021 Marek Chalupa
#
# SPDX-License-Identifier: Apache-2.0

from benchexec.tools.symbiotic import Tool as SymbioticTool
import benchexec.result as result


class Tool(SymbioticTool):
    """
    Symbiotic-Witch tool info object
    """

    def name(self):
        """
        Return the name of the tool, formatted for humans.
        """
        return "symbiotic-witch"

    def project_url(self):
        return "https://github.com/ayazip/witch"

    def _getPhase(self, output):
        lastphase = "initialization"
        for line in output:
            if line.startswith("INFO: Starting witness preprocessing"):
                lastphase = "validation preprocessing"
            if line.startswith("INFO: Done witness preprocessing"):
                lastphase = "compilation"
            if line.startswith("INFO: Starting instrumentation"):
                lastphase = "instrumentation"
            elif line.startswith("INFO: Instrumentation time"):
                lastphase = "instr-finished"
            elif line.startswith("INFO: Starting verification"):
                lastphase = "symbolic execution"
            elif line.startswith("INFO: Verification time"):
                lastphase = "verification-finished"

        return lastphase

    def determine_result(self, run):
        if not run.output:
            return f"{result.RESULT_ERROR}(no output)"

        for line in run.output:
            line = line.strip()

            if line.startswith("ERROR") and line.endswith("missing!"):
                return f"{result.RESULT_ERROR}(File missing)"

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
