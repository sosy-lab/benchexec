# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

from benchexec.tools.sv_benchmarks_util import get_data_model_from_task, ILP32, LP64
import benchexec.tools.template
import benchexec.result as result

import os


class Tool(benchexec.tools.template.BaseTool2):
    """
    DIVINE info object
    """

    BINS = ["divine", "rundivine", "lart", "clang", "opt"]
    LIBS = [
        "libc++abi.so.1",
        "libc.so.6",
        "libdl.so.2",
        "libm.so.6",
        "librt.so.1",
        "libunwind.so.1",
        "libc++.so.1",
        "libdivinert.bc",
        "libgcc_s.so.1",
        "libpthread.so.0",
        "libtinfo.so.5",
        "libz.so.1",
    ]

    def executable(self, tool_locator):
        """
        Find the path to the executable file that will get executed.
        This method always needs to be overridden,
        and most implementations will look similar to this one.
        The path returned should be relative to the current directory.
        """
        return tool_locator.find_executable(self.BINS[0], subdir="bin")

    def version(self, executable):
        return self._version_from_tool(executable)

    def name(self):
        """
        Return the name of the tool, formatted for humans.
        """
        return "DIVINE"

    def cmdline(self, executable, options, task, rlimits):
        """
        Compose the command line to execute from the name of the executable,
        the user-specified options, and the inputfile to analyze.
        This method can get overridden, if, for example, some options should
        be enabled or if the order of arguments must be changed.

        All paths passed to this method (executable, tasks, and propertyfile)
        are either absolute or have been made relative to the designated working directory.

        @param executable: the path to the executable of the tool (typically the result of executable())
        @param options: a list of options, in the same order as given in the XML-file.
        @param tasks: a list of tasks, that should be analysed with the tool in one run.
                            In most cases we we have only _one_ inputfile.
        @param propertyfile: contains a specification for the verifier.
        @param rlimits: This dictionary contains resource-limits for a run,
                        for example: time-limit, soft-time-limit, hard-time-limit, memory-limit, cpu-core-limit.
                        All entries in rlimits are optional, so check for existence before usage!
        """
        data_model_param = get_data_model_from_task(task, {ILP32: "--32", LP64: "--64"})
        if data_model_param and data_model_param not in options:
            options += [data_model_param]

        directory = os.path.dirname(executable)

        # Ignore propertyfile since we run only reachability
        run = (
            [os.path.join(".", directory, self.BINS[1]), directory]
            + options
            + list(task.input_files_or_identifier)
        )
        return run

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
        if not run.output:
            return "ERROR - no output"

        last = run.output[-1]

        if run.was_timeout:
            return result.RESULT_TIMEOUT

        if run.exit_code.value and run.exit_code.value != 0:
            return "ERROR - Pre-run"

        if "result: true" in last:
            return result.RESULT_TRUE_PROP
        elif "result: false" in last:
            return result.RESULT_FALSE_REACH
        else:
            return result.RESULT_UNKNOWN

    def program_files(self, executable):
        """
        OPTIONAL, this method is only necessary for situations when the benchmark environment
        needs to know all files belonging to a tool
        (to transport them to a cloud service, for example).
        Returns a list of files or directories that are necessary to run the tool.
        """
        directory = os.path.dirname(executable)
        return [os.path.join(".", directory, x) for x in self.BINS] + [
            os.path.join(".", directory, "..", "lib", x) for x in self.LIBS
        ]
