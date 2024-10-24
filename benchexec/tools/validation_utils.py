# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

"""
This module contains some useful functions for handling Validation Tasks
"""

from pathlib import Path

from benchexec.tools.template import UnsupportedFeatureException
import benchexec.tools.template


def __partition_input_files(task):
    input_files = task.input_files_or_identifier
    witness_files = []
    other_files = []
    for file in input_files:
        if Path(file).name == task.options.get("witness"):
            witness_files.append(file)
        else:
            other_files.append(file)
    return witness_files, other_files


def get_witness_input_files(task):
    witness_files, _ = __partition_input_files(task)
    return witness_files


def get_unique_witness(task):
    witness_files = get_witness_input_files(task)
    if len(witness_files) > 1:
        raise UnsupportedFeatureException(
            "Tool does not support multiple witness files"
        )
    return witness_files[0]


def get_non_witness_input_files(task):
    _, other_files = __partition_input_files(task)
    return other_files


def get_unique_non_witness_input_files(task):
    other_files = get_non_witness_input_files(task)
    if len(other_files) > 1:
        raise UnsupportedFeatureException("Tool does not support multiple input files")
    return other_files[0]


def add_witness_options(options, task, witness_options):
    additional_options = []
    if isinstance(task.options, dict) and "witness" in task.options.keys():
        if any(witness_option in options.keys() for witness_option in witness_options):
            for witness_option in witness_options:
                additional_options += [witness_option, get_unique_witness(task)]
        else:
            raise benchexec.tools.template.UnsupportedFeatureException(
                "You are passing a witness as both an option and through the task definition. "
                "Please remove one of them."
            )
    return additional_options
