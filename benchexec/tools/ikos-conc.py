# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2026 Ronghui Ruan
#
# SPDX-License-Identifier: Apache-2.0
"""BenchExec tool-info module for the IKOS concurrency (data-race) analysis.

Registers IKOS as an SV-COMP C.no-data-race tool:

  - cmdline(): fixes the analysis to `--analyses=race --concurrency=auto`,
    disables the (potentially multi-MB) per-check report in favour of the
    one-line summary verdict. Only the no-data-race property is supported.
  - determine_result(): maps the rendered verdict line back to the SV-COMP
    three-way result. Sound mapping under the FN=0/FP=0 red line: an explicit
    `The program is SAFE` yields TRUE; `definitely UNSAFE` (a race the bounded
    checker proved) yields FALSE; `potentially UNSAFE` (= UNKNOWN) and anything
    unparsed yield UNKNOWN.

Runnable standalone for local P1 validation:

    python3 benchexec/tools/ikos-conc.py <file.c|.i> [--property p.prp] \
        [--ikos /path/to/ikos] [--data-model ILP32|LP64]

which runs the bundled svcomp_witness.py wrapper (demote + BMC re-confirmation,
ILP32 by default) and prints TRUE / FALSE(no-data-race) / UNKNOWN.
"""

import re
import shutil
import subprocess
import sys
from pathlib import Path

# --- BenchExec interface (guarded so the module also runs standalone) ---
try:
    from benchexec import result
    from benchexec.tools.template import BaseTool2, UnsupportedFeatureException

    _TRUE, _FALSE, _UNKNOWN, _TIMEOUT = (
        result.RESULT_TRUE_PROP,
        result.RESULT_FALSE_PROP,
        result.RESULT_UNKNOWN,
        result.RESULT_TIMEOUT,
    )
except ImportError:  # pragma: no cover - standalone / offline test

    class BaseTool2:
        pass

    class UnsupportedFeatureException(ValueError):  # noqa: N818 - match BenchExec API
        pass

    _TRUE, _FALSE, _UNKNOWN, _TIMEOUT = "true", "false", "unknown", "timeout"


RE_DEF_UNSAFE = re.compile(r"\bThe program is definitely UNSAFE\b")
RE_UNKNOWN = re.compile(r"\bThe program is UNKNOWN\b")
RE_POT_UNSAFE = re.compile(r"\bThe program is potentially UNSAFE\b")
RE_SAFE = re.compile(r"\bThe program is SAFE\b")


def check_property(property_file):
    if property_file is None:
        return  # The standalone/default analysis is explicitly no-data-race.
    try:
        specification = Path(property_file).read_text(encoding="utf-8")
    except OSError as exc:
        raise UnsupportedFeatureException("Cannot read the property file") from exc
    if re.sub(r"\s+", "", specification) != "CHECK(init(main()),LTL(G!data-race))":
        raise UnsupportedFeatureException("IKOS-ConC supports only no-data-race")


def verdict_from_text(output):
    """Map rendered IKOS output to an SV-COMP result ('true'/'false'/'unknown').

    NOTE: "Total number of checks: 0" is the NORMAL summary for a race-free
    program — the checker only inserts a check when it finds a conflicting
    pair (or an unknown), so 0 checks + SAFE is correct, not a collapse.
    """
    # Priority mirrors report.py print_summary: definite-unsafe -> unknown ->
    # warning -> safe. "potentially UNSAFE" is a non-race warning (e.g. an
    # ignored side effect that "might be unsound"), so under FN=0 it must not
    # be TRUE.
    if RE_DEF_UNSAFE.search(output):
        return _FALSE
    if RE_UNKNOWN.search(output):
        return _UNKNOWN
    if RE_POT_UNSAFE.search(output):
        return _UNKNOWN
    if RE_SAFE.search(output):
        return _TRUE
    return _UNKNOWN


class Tool(BaseTool2):
    REQUIRED_PATHS = ["bin", "lib", "libexec", "llvm", "include"]

    def name(self):
        return "ikos-conc"

    def executable(self, tool_locator):
        return tool_locator.find_executable("ikos", subdir="bin")

    def program_files(self, executable):
        return self._program_files_from_executable(
            executable, self.REQUIRED_PATHS, parent_dir=True
        )

    def version(self, executable):
        # `ikos --version` prints "ikos 3.5" then the NASA license. Parse the
        # first line's last word so the reported version is "3.5", not the
        # last line ("All Rights Reserved.") that BaseTool2._version_from_tool
        # would return. Guard against a missing executable (offline test).
        try:
            out = subprocess.run(
                [executable, "--version"], capture_output=True, text=True, timeout=30
            ).stdout
            first = (out.strip().splitlines() or [""])[0].strip()
            return first.split()[-1] if first else ""
        except (OSError, subprocess.SubprocessError):
            return ""

    def cmdline(self, executable, options, task, rlimits):
        check_property(task.property_file)
        if task.options and not isinstance(task.options, dict):
            raise UnsupportedFeatureException("Expected C task options")
        task_options = task.options or {}
        if task_options.get("language", "C") != "C":
            raise UnsupportedFeatureException("IKOS-ConC supports C tasks")
        # Run svcomp_witness.py, bundled next to the tool executable (in the
        # archive's bin/): it forwards IKOS's verdict line to stdout (for
        # determine_result) and writes witness.yml on a race. The SV-COMP
        # property is checked above rather than forwarded. Locate the wrapper relative to
        # `executable`, not this module (which lives in the BenchExec repo).
        wrapper = Path(executable).parent / "svcomp_witness.py"
        cmd = [sys.executable, str(wrapper), "--ikos", executable]
        # Forward the task's data model (ILP32/LP64) so the .c/.i is compiled
        # with the right type widths and the witness's data_model field matches.
        # Always pass it explicitly: falling back to the wrapper's/host default
        # would silently analyze the wrong model. Metadata-free invocations
        # retain the documented ILP32 default.
        data_model = task_options.get("data_model") or "ILP32"
        if data_model not in ("ILP32", "LP64"):
            raise UnsupportedFeatureException(f"Unsupported data_model '{data_model}'")
        cmd += options
        cmd += ["--data-model", data_model]
        return cmd + [task.single_input_file]

    def determine_result(self, run):
        if run.was_timeout:
            return _TIMEOUT
        if run.exit_code.value != 0:
            # IKOS exits 0 on every verdict; a non-zero exit (or a signal,
            # exit_code.value is None) means compile/analyzer crash -> UNKNOWN.
            return _UNKNOWN
        return verdict_from_text(run.output.text)


# --- standalone P1 wrapper (python3 .../ikos-conc.py <file> [--property ...]) ---
if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("--property", default=None, help="no-data-race property file")
    ap.add_argument("--ikos", default=None)
    ap.add_argument("--data-model", default="ILP32", choices=["ILP32", "LP64"])
    ap.add_argument("--timeout", type=int, default=90)
    args = ap.parse_args()

    try:
        check_property(args.property)
    except UnsupportedFeatureException as exc:
        ap.error(str(exc))
    ikos = shutil.which(args.ikos or "ikos") or args.ikos or "ikos"
    ikos = str(Path(ikos).resolve())
    # Mirror cmdline(): run the bundled svcomp_witness.py wrapper (demote + BMC
    # re-confirmation + witness.yml) instead of ikos directly, and force ILP32
    # so the local test matches the competition (no-data-race is all ILP32).
    wrapper = Path(ikos).parent / "svcomp_witness.py"
    cmd = [
        sys.executable,
        str(wrapper),
        "--ikos",
        ikos,
        "--data-model",
        args.data_model,
        args.source,
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=args.timeout)
        out = proc.stdout + proc.stderr
        rc = proc.returncode
        timed_out = False
    except subprocess.TimeoutExpired:
        out = ""
        rc = -1
        timed_out = True
    except OSError:
        out, rc, timed_out = "", -1, False

    if timed_out or rc != 0:
        print("UNKNOWN")
    else:
        v = verdict_from_text(out)
        print({"true": "TRUE", "false": "FALSE(no-data-race)", "unknown": "UNKNOWN"}[v])
