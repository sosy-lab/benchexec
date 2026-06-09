# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import os

import benchexec.tools.template
from benchexec.result import RESULT_ERROR, RESULT_TRUE_PROP


class Tool(benchexec.tools.template.BaseTool2):
    """
    VeriPB is a proof checker for the pseudo-Boolean proof format, a strictly more
    expressive generalization of DRAT that can certify advanced reasoning techniques
    such as symmetry breaking, XOR reasoning, and dominance breaking.

    Supports the Python-based static binary (veripb_bin_static, version < 3) and the
    Rust rewrite (veripb, version 3+).
    """

    def executable(self, tool_locator):
        # Prefer the new Rust binary; fall back to the old static Python binary.
        try:
            return tool_locator.find_executable("veripb")
        except benchexec.tools.template.ToolNotFoundException:
            return tool_locator.find_executable("veripb_bin_static")

    def name(self):
        return "VeriPB"

    def project_url(self):
        return "https://gitlab.com/MIAOresearch/software/VeriPB"

    def version(self, executable):
        if os.path.basename(executable) == "veripb_bin_static":
            # Old Python binary prints "Running VeriPB version X.X.X" on every run
            return self._version_from_tool(
                executable, arg="-h", line_prefix="Running VeriPB version "
            )
        # New Rust binary (v3+) uses clap; --version prints "veripb X.X.X".
        version = self._version_from_tool(executable)
        return version.removeprefix("veripb ").strip()

    def cmdline(self, executable, options, task, rlimits):
        return [executable, task.single_input_file, *options]

    def determine_result(self, run):
        for line in reversed(run.output):
            if line.startswith("Verification Succeeded."):
                return RESULT_TRUE_PROP

        return RESULT_ERROR
