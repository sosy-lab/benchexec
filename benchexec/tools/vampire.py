# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec
import benchexec.result as result


class Tool(benchexec.tools.template.BaseTool2):
    """
    Tool info for Vampire.
    """

    def name(self):
        return "Vampire"

    def project_url(self):
        return "https://github.com/vprover/vampire"

    def executable(self, tool_locator):
        return tool_locator.find_executable("vampire")

    def version(self, executable):
        line = self._version_from_tool(executable, line_prefix="Vampire")
        line = line.strip()
        line = line.split(" ")[0]
        return line.strip()

    def environment(self, executable):
        return {"keepEnv": {"TPTP": 1}}

    def cmdline(self, executable, options, task, rlimits):
        if "-t" not in options and "--time_limit" not in options:
            # Default timeout of Vampire is 60s, so we set value of 0
            # explicitly (i.e. unlimited) if rlimits.walltime is None
            options += ["-t", f"{rlimits.walltime or 0}s"]

        # TODO: should we warn if the memory is not set explicitly?
        # Vampire is going to use the default of 3000MiB in this case
        if "-m" not in options and "--memory_limit" not in options and rlimits.memory:
            # Vampire's option '--memory_limit/-m' takes the value in MiB
            memory_mib = rlimits.memory // (1024 * 1024)
            options += ["-m", str(memory_mib)]

        return [executable, *options, task.single_input_file]

    def determine_result(self, run):
        status = self.get_szs_status(run.output)
        if run.exit_code:
            if status == "Timeout":
                return result.RESULT_TIMEOUT
            if run.exit_code.value == 4:
                # Some kind of system error happened
                if run.output.text.startswith("Parsing Error"):
                    return "PARSING ERROR"
            if run.exit_code.value == 1:
                # Error during portfolio mode
                if run.output.text.startswith("% Exception at proof search level\n"):
                    if any(line.startswith("Parsing Error") for line in run.output):
                        return "PARSING ERROR"
                # Not really an error but unable to finish
                reasons = self.get_other_termination_reasons(run.output)
                if reasons == ["Time limit"]:
                    return result.RESULT_TIMEOUT
                if reasons == ["Memory limit"]:
                    return "OUT OF MEMORY"
                if reasons == ["Refutation not found, incomplete strategy"]:
                    return "INCOMPLETE"
                if reasons == ["Refutation not found, non-redundant clauses discarded"]:
                    return "INCOMPLETE"
            # Some other error
            return result.RESULT_ERROR
        else:
            # Successfully finished
            if status in self.SZS_UNSAT:
                return result.RESULT_TRUE_PROP
            elif status in self.SZS_SAT:
                return result.RESULT_FALSE_PROP
            else:
                return result.RESULT_UNKNOWN

    # SZS status values that Vampire returns
    SZS_UNSAT = ["ContradictoryAxioms", "Theorem", "Unsatisfiable"]
    SZS_SAT = ["CounterSatisfiable", "Satisfiable"]
    SZS_FAIL = ["Timeout", "GaveUp", "User"]

    def get_szs_status(self, output):
        """
        Extract the SZS status from the output.
        @param output: The output of the tool as instance of class RunOutput.
        @return a non-empty string, or None if no unique SZS status was found
        """
        status = None
        for line in output:
            if line.startswith("% SZS status"):
                if status is None:
                    words = line.split()
                    status = words[3] if len(words) >= 4 else None
                else:
                    # More than one SZS status => this is an error!
                    return None
        return status

    def get_other_termination_reasons(self, output):
        """
        Extract termination reasons from the output from lines starting with '% Termination reason'.
        @param output: The output of the tool as instance of class RunOutput.
        @return List of strings, the termination found in the output (without prefix).
        """
        prefix = "% Termination reason: "
        reasons = []
        for line in output:
            if line.startswith(prefix):
                reasons.append(line[len(prefix) :])
        return reasons

    def get_value_from_output(self, output, identifier):
        if identifier == "szs-status":
            return self.get_szs_status(output)
        return None
