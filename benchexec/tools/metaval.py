# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import argparse
import benchexec.tools.template
import os
import re
import threading

from benchexec.tools.template import BaseTool2
from benchexec.tools.template import UnsupportedFeatureException


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
    REQUIRED_PATHS = list(TOOL_TO_PATH_MAP.values()) + [
        "VERSION.txt",
        "metaval.py",
        "metaval.sh",
    ]

    def __init__(self):
        self.lock = threading.Lock()
        self.wrappedTools = {}

    def executable(self, toolLocator):
        return toolLocator.find_executable("metaval.sh")

    def name(self):
        return "MetaVal"

    def project_url(self):
        return "https://gitlab.com/sosy-lab/software/metaval"

    def determine_result(self, run):
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
        assert isinstance(
            tool, BaseTool2
        ), "we expect that all wrapped tools extend BaseTool2"
        return tool.determine_result(run)

    def cmdline(self, executable, options, task, rlimits):
        if not task.property_file:
            raise UnsupportedFeatureException(
                f"Execution without property file is not supported by {self.name()}!"
            )
        parser = argparse.ArgumentParser(add_help=False, usage=argparse.SUPPRESS)
        parser.add_argument("--metavalWitness", required=True)
        parser.add_argument("--metavalVerifierBackend", required=True)
        parser.add_argument("--metavalAdditionalPATH")
        parser.add_argument("--metavalWitnessType")
        (knownargs, options) = parser.parse_known_args(options)
        verifierName = knownargs.metavalVerifierBackend.lower()
        witnessName = knownargs.metavalWitness
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
        assert isinstance(
            tool, BaseTool2
        ), "we expect that all wrapped tools extend BaseTool2"
        wrapped_executable = tool.executable(
            BaseTool2.ToolLocator(
                tool_directory=self._resource(
                    executable, self.TOOL_TO_PATH_MAP[verifierName]
                )
            )
        )
        wrappedtask = BaseTool2.Task(
            input_files=[self._resource(executable, "output/ARG.c")],
            identifier=task.identifier,
            property_file=task.property_file,
            options=task.options,
        )
        wrappedOptions = tool.cmdline(
            wrapped_executable,
            options,
            wrappedtask,
            rlimits,
        )

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
            + [task.single_input_file]
            + ["--"]
            + wrappedOptions
        )

    def _resource(self, executable, relpath):
        return os.path.join(os.path.dirname(executable), relpath)

    def version(self, executable):
        stdout = self._version_from_tool(executable, "--version")
        metavalVersion = stdout.splitlines()[0].strip()
        return metavalVersion
