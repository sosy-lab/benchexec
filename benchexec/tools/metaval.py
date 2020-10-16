# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import argparse
import benchexec.util as util
import benchexec.tools.template
import contextlib
import os
import re
import sys
import threading


class Tool(benchexec.tools.template.BaseTool):
    """
    This is the tool info module for MetaVal.

    The official repository is:
    https://gitlab.com/sosy-lab/software/metaval

    Please report any issues to our issue tracker at:
    https://gitlab.com/sosy-lab/software/metaval/issues

    """

    TOOL_TO_PATH_MAP = {
        "cpachecker-metaval": "CPAchecker",
        "cpachecker": "CPAchecker-1.7-svn 29852-unix",
        "esbmc": "esbmc",
        "symbiotic": "symbiotic",
        "yogar-cbmc": "yogar-cbmc",
        "ultimateautomizer": "UAutomizer-linux",
    }
    PATH_TO_TOOL_MAP = {v: k for k, v in TOOL_TO_PATH_MAP.items()}
    REQUIRED_PATHS = list(TOOL_TO_PATH_MAP.values())

    def __init__(self):
        self.lock = threading.Lock()
        self.wrappedTools = {}

    def executable(self):
        return util.find_executable("metaval.sh")

    def name(self):
        return "metaval"

    @contextlib.contextmanager
    def _in_tool_directory(self, verifierName):
        """
        Context manager that sets the current working directory to the tool's directory
        and resets its afterward. The returned value is the previous working directory.
        """
        with self.lock:
            try:
                oldcwd = os.getcwd()
                os.chdir(os.path.join(oldcwd, self.TOOL_TO_PATH_MAP[verifierName]))
                yield oldcwd
            finally:
                os.chdir(oldcwd)

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        verifierDir = None
        regex = re.compile("verifier used in MetaVal is (.*)")
        for line in output[:20]:
            match = regex.match(line)
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
        with self._in_tool_directory(verifierName):
            return self.wrappedTools[verifierName].determine_result(
                returncode, returnsignal, output, isTimeout
            )

    def cmdline(self, executable, options, tasks, propertyfile=None, rlimits={}):
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

        if verifierName in self.wrappedTools:
            with self._in_tool_directory(verifierName) as oldcwd:
                wrappedOptions = self.wrappedTools[verifierName].cmdline(
                    self.wrappedTools[verifierName].executable(),
                    options,
                    [os.path.relpath(os.path.join(oldcwd, "output/ARG.c"))],
                    os.path.relpath(os.path.join(oldcwd, propertyfile)),
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
                + tasks
                + ["--"]
                + wrappedOptions
            )
        else:
            sys.exit("ERROR: Could not find wrapped tool")  # noqa: R503 always raises

    def version(self, executable):
        stdout = self._version_from_tool(executable, "--version")
        metavalVersion = stdout.splitlines()[0].strip()
        return metavalVersion
