# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
# SPDX-FileCopyrightText: 2026 Xinyu Zhang
# SPDX-License-Identifier: Apache-2.0

"""Single-task C2Btor/Carat verification with SV-COMP YAML 2.1 witnesses."""

import importlib.util
import os
import sys
from pathlib import Path

from benchexec import result
from benchexec.tools.template import BaseTool2, UnsupportedFeatureException


class Tool(BaseTool2):
    """C2Btor and Carat single-task verifier with YAML 2.1 witness delivery."""

    # Runtime archive layout: bin/ and scripts/.
    # Source-checkout layout: build/bin/ and checkers/carat/...
    # Missing alternatives are ignored by program_files().
    REQUIRED_PATHS = [
        "bin/",
        "scripts/",
        "build/bin/c2btor",
        "checkers/carat/build/carat",
        "checkers/carat/deps/btor2tools/build/bin/btorsim",
    ]

    def executable(self, tool_locator):
        return tool_locator.find_executable("c2btor-verify")

    def name(self):
        return "C2Btor"

    def version(self, executable):
        return self._version_from_tool(executable)

    def program_files(self, executable):
        files = [
            executable,
            *self._program_files_from_executable(executable, self.REQUIRED_PATHS),
        ]
        # Development overrides name actual runtime executables, rather than
        # assuming binaries elsewhere in the user's original checkout exist.
        for name in ("C2BTOR", "CARAT", "BTORSIM"):
            path = os.environ.get(name)
            if path and Path(path).is_file():
                files.append(str(Path(path).resolve()))
        # Include the selected Python and the actual schema/YAML dependencies
        # used by that installation (a bundled runtime/ is included above).
        files.append(sys.executable)
        for name in (
            "yaml",
            "jsonschema",
            "referencing",
            "rpds",
            "attrs",
            "attr",
            "jsonschema_specifications",
        ):
            spec = importlib.util.find_spec(name)
            if spec:
                files.extend(list(spec.submodule_search_locations or [spec.origin]))
        return list(dict.fromkeys(files))

    def cmdline(self, executable, options, task, rlimits):
        task_options = task.options or {}
        if task_options.get("language") != "C":
            raise UnsupportedFeatureException("C2Btor requires a C task")
        if not task.property_file:
            raise UnsupportedFeatureException(
                "C2Btor requires an unreach-call property file"
            )
        data_model = task_options.get("data_model")
        if data_model not in {"ILP32", "LP64"}:
            raise UnsupportedFeatureException("C2Btor requires ILP32 or LP64")
        return [
            executable,
            task.single_input_file,
            "--property",
            task.property_file,
            "--data-model",
            data_model,
            *options,
        ]

    def determine_result(self, run):
        if run.was_timeout:
            return result.RESULT_TIMEOUT
        if run.exit_code or run.was_terminated:
            return result.RESULT_ERROR
        verdicts = {
            "Verification result: TRUE": result.RESULT_TRUE_PROP,
            "Verification result: FALSE(unreach-call)": result.RESULT_FALSE_REACH,
            "Verification result: UNKNOWN": result.RESULT_UNKNOWN,
            "Verification result: ERROR": result.RESULT_ERROR,
        }
        for line in reversed(run.output):
            if line.strip() in verdicts:
                return verdicts[line.strip()]
        return result.RESULT_UNKNOWN
