# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.tools.template
from benchexec import result
from benchexec.tools.sv_benchmarks_util import ILP32, LP64, get_data_model_from_task
from benchexec.tools.template import UnsupportedFeatureException


class Tool(benchexec.tools.template.BaseTool2):
    """
    Tool info for SAF (Static Analyzer Factory), an analyzer for C programs.

    SAF is run through its "verify" subcommand, which writes exactly one
    verdict line to stdout, "true", "false(<subproperty>)" or "unknown" (also
    when SAF gives up by itself), and every diagnostic message to stderr. It
    exits with code 0 whenever it reports a verdict; any other exit is an error.

    A property file is required: SAF reads the CHECK(... LTL ...) directive out
    of the given .prp file, so this module rejects tasks without one. The data
    model of the task, if it defines one, is passed as "--data-model"; SAF
    assumes LP64 otherwise. All further options are passed on unchanged.

    SAF finds its data files (stub headers and function specifications) in
    share/saf/ relative to its executable in bin/, so these two directories
    have to stay siblings.
    """

    REQUIRED_PATHS = ["bin", "share"]

    def executable(self, tool_locator):
        return tool_locator.find_executable("saf", subdir="bin")

    def program_files(self, executable):
        # REQUIRED_PATHS are relative to the tool directory, which is the parent
        # of the directory of the executable.
        return [executable] + self._program_files_from_executable(
            executable, self.REQUIRED_PATHS, parent_dir=True
        )

    def name(self):
        return "SAF"

    def project_url(self):
        return "https://github.com/Static-Analyzer-Factory/static-analyzer-factory"

    def version(self, executable):
        # `saf --version` prints "saf 0.1.0 (LLVM 18.1)".
        return self._version_from_tool(executable, line_prefix="saf ")

    def cmdline(self, executable, options, task, rlimits):
        if not task.property_file:
            raise UnsupportedFeatureException(
                "SAF needs a property file and cannot verify without one"
            )

        # SAF spells the data model exactly like the task definition does.
        data_model = get_data_model_from_task(task, {ILP32: ILP32, LP64: LP64})

        cmd = [executable, "verify", "--property", task.property_file]
        if data_model and "--data-model" not in options:
            cmd += ["--data-model", data_model]
        cmd += options
        # SAF analyzes one program, either C source or preprocessed C source.
        cmd.append(task.single_input_file)
        return cmd

    def determine_result(self, run):
        if run.exit_code.value != 0:
            # A crash, a kill by a signal, or another abnormal termination.
            return result.RESULT_ERROR

        for line in run.output:
            if line in (result.RESULT_TRUE_PROP, result.RESULT_UNKNOWN):
                return line
            if line == result.RESULT_FALSE_PROP or (
                line.startswith(result.RESULT_FALSE_PROP + "(") and line.endswith(")")
            ):
                # The verdict names the violated subproperty, as in
                # "false(valid-deref)".
                return line

        return result.RESULT_ERROR
