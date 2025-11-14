# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import argparse
import os
import re
import threading
from typing import Optional

import benchexec.tools.template
from benchexec.tools.sv_benchmarks_util import (
    get_witness,
    get_single_non_witness_input_file,
    WITNESS_INPUT_FILE_IDENTIFIER,
)
from benchexec.tools.template import (
    BaseTool2,
    UnsupportedFeatureException,
    ToolNotFoundException,
)


class Tool(benchexec.tools.template.BaseTool2):
    """
    This is the tool info module for MetaVal.

    The official repository is:
    https://gitlab.com/sosy-lab/software/metaval

    Please report any issues to our issue tracker at:
    https://gitlab.com/sosy-lab/software/metaval/issues

    """

    TOOL_TO_PATH_MAP = {
        "cpachecker-metaval": "CPAchecker-frontend",
        "cpachecker": "CPAchecker",
        "esbmc": "esbmc",
        "symbiotic": "symbiotic",
        "yogar-cbmc": "yogar-cbmc",
        "ultimateautomizer": "UAutomizer-linux",
    }
    PATH_TO_TOOL_MAP = {v: k for k, v in TOOL_TO_PATH_MAP.items()}

    def __init__(self):
        self.lock = threading.Lock()
        self.wrappedTools = {}
        self._cached_version: Optional[str] = None

    def executable(self, tool_locator):
        try:
            return tool_locator.find_executable("metaval.sh")
        except ToolNotFoundException as e1:
            try:
                return tool_locator.find_executable("metaval.py")
            except ToolNotFoundException:
                raise e1

    def program_files_version_less_two(self, executable):
        return [
            "VERSION.txt",
            "metaval.py",
            "metaval.sh",
        ] + [
            self._resource(executable, path) for path in self.PATH_TO_TOOL_MAP.values()
        ]

    def program_files(self, executable):
        if self.is_version_less_than_two(executable):
            return self.program_files_version_less_two(executable)

    def name(self):
        return "MetaVal"

    def project_url(self):
        return "https://gitlab.com/sosy-lab/software/metaval"

    def is_version_less_than_two(self, executable):
        version_string = self.version(executable)
        major_version_match = re.match(r"(\d+)\..*", version_string)
        if major_version_match:
            major_version = int(major_version_match.group(1))
            return major_version < 2
        return False

    def determine_result_version_less_two(self, run):
        verifierDir = None
        regex = re.compile("verifier used in MetaVal is (.*)")
        for line in run.output[:20]:
            match = regex.search(line)
            if match is not None:
                verifierDir = match.group(1)
                break
        if (
            not verifierDir
            or verifierDir not in self.PATH_TO_TOOL_MAP
            or self.PATH_TO_TOOL_MAP[verifierDir] not in self.wrappedTools
        ):
            return "METAVAL ERROR"
        verifierName = self.PATH_TO_TOOL_MAP[verifierDir]

        tool = self.wrappedTools[verifierName]
        assert isinstance(tool, BaseTool2), (
            "we expect that all wrapped tools extend BaseTool2"
        )
        return tool.determine_result(run)

    def determine_result(self, run):
        if self.is_version_less_than_two(None):
            return self.determine_result_version_less_two(run)

    def cmdline_version_less_two(self, executable, options, task, rlimits):
        if not task.property_file:
            raise UnsupportedFeatureException(
                f"Execution without property file is not supported by {self.name()}!"
            )
        parser = argparse.ArgumentParser(add_help=False, usage=argparse.SUPPRESS)
        parser.add_argument("--metavalWitness", default=None)
        parser.add_argument("--metavalVerifierBackend", required=True)
        parser.add_argument("--metavalAdditionalPATH")
        parser.add_argument("--metavalWitnessType")
        (knownargs, options) = parser.parse_known_args(options)
        verifierName = knownargs.metavalVerifierBackend.lower()
        witnessName = knownargs.metavalWitness
        if knownargs.metavalWitness is None:
            witnessName = get_witness(task)

        additionalPathArgument = (
            ["--additionalPATH", knownargs.metavalAdditionalPATH]
            if knownargs.metavalAdditionalPATH
            else []
        )
        witnessTypeArgument = (
            ["--witnessType", knownargs.metavalWitnessType]
            if knownargs.metavalWitnessType
            else []
        )
        with self.lock:
            if verifierName not in self.wrappedTools:
                self.wrappedTools[verifierName] = __import__(
                    "benchexec.tools." + verifierName, fromlist=["Tool"]
                ).Tool()

        tool = self.wrappedTools[verifierName]
        assert isinstance(tool, BaseTool2), (
            "we expect that all wrapped tools extend BaseTool2"
        )
        wrapped_executable = tool.executable(
            BaseTool2.ToolLocator(
                tool_directory=self._resource(
                    executable, self.TOOL_TO_PATH_MAP[verifierName]
                )
            )
        )
        wrapped_tasks_options = task.options
        if isinstance(wrapped_tasks_options, dict):
            wrapped_tasks_options = {
                k: v
                for k, v in wrapped_tasks_options.items()
                if k != WITNESS_INPUT_FILE_IDENTIFIER
            }
        wrappedtask = BaseTool2.Task(
            input_files=[self._resource(executable, "output/ARG.c")],
            identifier=task.identifier,
            property_file=task.property_file,
            options=wrapped_tasks_options,
        )
        wrappedOptions = tool.cmdline(
            wrapped_executable,
            options,
            wrappedtask,
            rlimits,
        )

        input_file = get_single_non_witness_input_file(task)

        return (
            [
                executable,
                "--verifier",
                self.TOOL_TO_PATH_MAP[verifierName],
                "--witness",
                witnessName,
            ]
            + additionalPathArgument
            + witnessTypeArgument
            + ["--property", task.property_file]
            + [input_file]
            + ["--"]
            + wrappedOptions
        )

    def cmdline(self, executable, options, task, rlimits):
        if self.is_version_less_than_two(executable):
            return self.cmdline_version_less_two(executable, options, task, rlimits)

    def _resource(self, executable, relpath):
        return os.path.join(os.path.dirname(executable), relpath)

    def version(self, executable):
        if self._cached_version is not None:
            return self._cached_version

        stdout = self._version_from_tool(executable, "--version")
        metaval_version = stdout.splitlines()[0].strip()
        self._cached_version = metaval_version
        return metaval_version
