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

    SAF is run through its "verify" subcommand, which is its SV-COMP entry
    point. That subcommand writes exactly one verdict line to stdout, always one
    of the BenchExec RESULT_* strings, and every diagnostic message to stderr.

    SAF reports "true", "false(<subproperty>)" (for example
    "false(unreach-call)" or "false(valid-deref)") or "unknown"; properties it
    has no strategy for, and tasks it cannot decide, yield "unknown". This
    module accepts any RESULT_* verdict that SAF prints, so it does not need to
    change when SAF learns a new property or subproperty.

    A property file is required. SAF reads the CHECK(... LTL ...) directive out
    of the given .prp file and never looks at the file name, so it cannot run
    without one, and this module rejects tasks that have no property file.

    This module adds two arguments of its own:
      --property <file>        the property file of the task
      --data-model ILP32|LP64  the data model, when the task defines one; SAF
                               assumes LP64 otherwise
    All further arguments are taken from the benchmark definition and passed on
    unchanged. The useful ones are "--witness <file>", the path that SAF writes
    the witness of a task to, and "--timeout <seconds>", a wall-clock budget
    after which SAF reports "unknown" by itself instead of waiting to be killed.
    Neither is required: SAF defaults to "witness.yml", the name that SV-COMP
    expects, and to a budget slightly below the SV-COMP time limit. Note that
    BenchExec does not expand ${witness} inside option values, so if a witness
    file name is given here at all it has to be spelled out literally.

    The tool archive has the executable in bin/saf and the data files that SAF
    needs, stub headers and function specifications, under share/saf/. SAF
    looks for the latter relative to its own executable, so those two
    directories have to stay siblings.
    """

    REQUIRED_PATHS = ["bin", "share"]

    def executable(self, tool_locator):
        return tool_locator.find_executable("saf", subdir="bin")

    def program_files(self, executable):
        # REQUIRED_PATHS are relative to the archive root, and the executable
        # lives in bin/ below it, so the base directory is the parent one.
        return [executable] + self._program_files_from_executable(
            executable, self.REQUIRED_PATHS, parent_dir=True
        )

    def name(self):
        return "SAF"

    def project_url(self):
        return "https://github.com/Static-Analyzer-Factory/static-analyzer-factory"

    def version(self, executable):
        # `saf --version` prints a single line, and clap prefixes it with the
        # binary name: "saf 0.1.0 (LLVM 18.1)". fm-tools' ci/check_archive.py
        # REJECTS an archive whose version string starts with the name this
        # module reports, so strip that leading token. The comparison is
        # deliberately case-insensitive: name() is "SAF" and clap prints "saf",
        # so today the check passes only by accident, and renaming either one
        # would silently fail the archive. Extra lines are dropped because a
        # version containing a newline is rejected by the same script.
        version = self._version_from_tool(executable)
        version = version.splitlines()[0].strip() if version else ""
        prefix = self.name().lower() + " "
        if version.lower().startswith(prefix):
            version = version[len(prefix) :].strip()
        return version

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
        if run.exit_code is not None and run.exit_code.signal:
            # SAF was killed. A verdict that it managed to flush just before
            # that is not trustworthy, and reporting it would have it scored,
            # because BenchExec replaces only the unspecific results of
            # result.RESULT_LIST_OTHER by a more precise status. So report
            # nothing and let BenchExec turn this into TIMEOUT, KILLED,
            # ABORTED or SEGMENTATION FAULT.
            return result.RESULT_UNKNOWN

        for line in run.output:
            verdict = line.strip()
            if verdict in (result.RESULT_TRUE_PROP, result.RESULT_UNKNOWN):
                return verdict
            if verdict == result.RESULT_FALSE_PROP or (
                verdict.startswith(result.RESULT_FALSE_PROP + "(")
                and verdict.endswith(")")
            ):
                # SV-COMP properties name a subproperty in the verdict, as in
                # "false(valid-deref)". This is the same shape that
                # result.get_result_classification() accepts.
                return verdict

        # SAF printed no verdict at all. Reporting unknown lets BenchExec
        # replace it by TIMEOUT or OUT OF MEMORY where that applies.
        return result.RESULT_UNKNOWN
