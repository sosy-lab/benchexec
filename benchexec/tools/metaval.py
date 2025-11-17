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

import benchexec.tools.template
from benchexec.tools.sv_benchmarks_util import (
    get_witness,
    get_single_non_witness_input_file,
    WITNESS_INPUT_FILE_IDENTIFIER,
    get_data_model_from_task,
    TaskFilesConsidered,
    handle_witness_of_task,
    LP64,
    ILP32,
)
from benchexec.tools.template import (
    BaseTool2,
    UnsupportedFeatureException,
    ToolNotFoundException,
)


class MetaVal1:
    TOOL_TO_PATH_MAP = {
        "cpachecker-metaval": "CPAchecker-frontend",
        "cpachecker": "CPAchecker",
        "esbmc": "esbmc",
        "symbiotic": "symbiotic",
        "yogar-cbmc": "yogar-cbmc",
        "ultimateautomizer": "UAutomizer-linux",
    }
    PATH_TO_TOOL_MAP = {v: k for k, v in TOOL_TO_PATH_MAP.items()}

    REQUIRED_PATHS = [
        "VERSION.txt",
        "metaval.py",
    ] + list(TOOL_TO_PATH_MAP.values())

    def __init__(self):
        self.lock = threading.Lock()
        self.wrappedTools = {}

    def executable(self, tool_locator):
        return tool_locator.find_executable("metaval.sh")

    def program_files(self, executable):
        return [executable] + BaseTool2._program_files_from_executable(
            executable, self.REQUIRED_PATHS
        )

    def _resource(self, executable, relpath):
        return os.path.join(os.path.dirname(executable), relpath)

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
        assert isinstance(tool, BaseTool2), (
            "we expect that all wrapped tools extend BaseTool2"
        )
        return tool.determine_result(run)

    def cmdline(self, executable, options, task, rlimits):
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

    def get_value_from_output(self, output, identifier):
        return None


class MetaVal2:
    def program_files(self, executable):
        return [executable] + BaseTool2._program_files_from_executable(
            executable, ["lib", "src", "config"]
        )

    def executable(self, tool_locator):
        return tool_locator.find_executable("metaval.py")

    def cmdline(self, executable, options, task, rlimits):
        if task.property_file:
            options = options + ["--property", task.property_file]

        data_model_param = get_data_model_from_task(
            task, {ILP32: "ILP32", LP64: "LP64"}
        )

        if data_model_param and "--data-model" not in options:
            options += ["--data-model", data_model_param]

        input_file, witness_options = handle_witness_of_task(
            task, options, "--witness", TaskFilesConsidered.SINGLE_INPUT_FILE
        )

        program_options = ["--program", input_file[0]]

        return [executable] + options + witness_options + program_options

    def determine_result(self, run):
        separator = ":"
        if not run.output:
            return benchexec.result.RESULT_ERROR
        lastline = run.output[-1]
        if lastline.startswith("Witness is correct"):
            return benchexec.result.RESULT_TRUE_PROP
        elif lastline.startswith("Witness is incorrect"):
            return benchexec.result.RESULT_FALSE_PROP
        elif any(
            lastline.startswith(start_identifier)
            for start_identifier in (
                "Witness could not be validated",
                "There was an error validating the witness",
            )
        ):
            prefix = (
                benchexec.result.RESULT_UNKNOWN
                if lastline.startswith("Witness could not be validated")
                else benchexec.result.RESULT_ERROR
            )
            if separator in lastline:
                return (
                    prefix
                    + "("
                    + lastline.split(separator, maxsplit=1)[1].strip()
                    + ")"
                )
            else:
                return prefix
        elif lastline.startswith("Witness file does not exist"):
            return benchexec.result.RESULT_ERROR + "(no witness)"
        else:
            return benchexec.result.RESULT_ERROR

    def get_value_from_output(self, output, identifier):
        # Search the text line per line using the regex passed as identifier
        # and return the first match found.
        for line in output:
            matches = re.search(identifier, line)
            if matches:
                return matches.group()
        return None


class Tool(benchexec.tools.template.BaseTool2):
    """
    This is the tool info module for MetaVal.

    The official repository is:
    https://gitlab.com/sosy-lab/software/metaval

    Please report any issues to our issue tracker at:
    https://gitlab.com/sosy-lab/software/metaval/issues

    """

    def __init__(self):
        self._delegate: MetaVal1 | MetaVal2 = MetaVal1()

    def executable(self, tool_locator):
        try:
            return self._delegate.executable(tool_locator)
        except ToolNotFoundException as e1:
            try:
                self._delegate = MetaVal2()
                return self._delegate.executable(tool_locator)
            except ToolNotFoundException:
                raise e1

    def program_files(self, executable):
        return self._delegate.program_files(executable)

    def name(self):
        return "MetaVal"

    def project_url(self):
        return "https://gitlab.com/sosy-lab/software/metaval"

    def determine_result(self, run):
        return self._delegate.determine_result(run)

    def cmdline(self, executable, options, task, rlimits):
        return self._delegate.cmdline(executable, options, task, rlimits)

    def version(self, executable):
        stdout = self._version_from_tool(executable, "--version")
        return stdout.splitlines()[0].strip()

    def get_value_from_output(self, output, identifier):
        return self._delegate.get_value_from_output(output, identifier)
