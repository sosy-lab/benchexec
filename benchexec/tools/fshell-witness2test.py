# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import re

import benchexec.result as result
import benchexec.tools.template
from benchexec.tools.sv_benchmarks_util import get_data_model_from_task, ILP32, LP64


class Tool(benchexec.tools.template.BaseTool2):
    """
    Tool info for witness2test
    """

    def executable(self, tool_locator):
        """
        Find the path to the executable file that will get executed.
        @return a string pointing to an executable file
        """
        return tool_locator.find_executable("test-gen.sh")

    def version(self, executable):
        return self._version_from_tool(executable)

    def name(self):
        """
        Return the name of the tool, formatted for humans.
        @return a non-empty string
        """
        return "CProver witness2test"

    def project_url(self):
        return "https://github.com/diffblue/cprover-sv-comp/pull/14"

    def cmdline(self, executable, options, task, rlimits):
        """
        Compose the command line to execute from the name of the executable,
        the user-specified options, and the inputfile to analyze.

        All paths passed to this method (executable, tasks, and propertyfile)
        are either absolute or have been made relative to the designated working directory.

        @param executable: the path to the executable of the tool (typically the result of executable())
        @param options: a list of options, in the same order as given in the XML-file.
        @param tasks: a list of tasks, that should be analysed with the tool in one run.
                            A typical run has only one input file, but there can be more than one.
        @param propertyfile: contains a specification for the verifier (optional, not always present).
        @param rlimits: This dictionary contains resource-limits for a run,
                        for example: time-limit, soft-time-limit, hard-time-limit, memory-limit, cpu-core-limit.
                        All entries in rlimits are optional, so check for existence before usage!
        @return a list of strings that represent the command line to execute
        """
        if task.property_file:
            options = options + ["--propertyfile", task.property_file]

        data_model_param = get_data_model_from_task(task, {ILP32: "-m32", LP64: "-m64"})
        if data_model_param and data_model_param not in options:
            options += [data_model_param]

        return [executable] + options + list(task.input_files_or_identifier)

    def determine_result(self, run):
        """
        Parse the output of the tool and extract the verification result.
        This method always needs to be overridden.
        If the tool gave a result, this method needs to return one of the
        benchexec.result.RESULT_* strings.
        Otherwise an arbitrary string can be returned that will be shown to the user
        and should give some indication of the failure reason
        (e.g., "CRASH", "OUT_OF_MEMORY", etc.).
        @param run.exit_code.value: the exit code of the program, None if the program was killed
        @param runb.exi_code.signal: the signal that killed the program, None if program exited itself
        @param output: a list of strings of output lines of the tool (both stdout and stderr)
        @param isTimeout: whether the result is a timeout
        (useful to distinguish between program killed because of error and timeout)
        @return a non-empty string, usually one of the benchexec.result.RESULT_* constants
        """
        output = run.output
        status = result.RESULT_ERROR
        if run.exit_code.value == 0:
            if output:
                result_str = output[-1].strip()

                if result_str == "TRUE":
                    status = result.RESULT_TRUE_PROP
                elif "FALSE" in result_str:
                    if result_str == "FALSE(valid-memtrack)":
                        status = result.RESULT_FALSE_MEMTRACK
                    elif result_str == "FALSE(valid-deref)":
                        status = result.RESULT_FALSE_DEREF
                    elif result_str == "FALSE(valid-free)":
                        status = result.RESULT_FALSE_FREE
                    elif result_str == "FALSE(no-overflow)":
                        status = result.RESULT_FALSE_OVERFLOW
                    else:
                        status = result.RESULT_FALSE_REACH
                elif "UNKNOWN" in output:
                    status = result.RESULT_UNKNOWN
        elif (
            output
            and re.match(r"^INVALID WITNESS FILE", output[-1].strip()) is not None
        ):
            status += " (invalid witness file)"

        return status
