# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

"""
This module contains some useful functions related to tasks in the sv-benchmarks
repository: https://gitlab.com/sosy-lab/benchmarking/sv-benchmarks

Note the following points before using any function in this util:
    1. This is not a part of stable benchexec API.
       We do not provide any guarantee of backward compatibility of this module.
    2. Out-of-tree modules should not use this util
    3. Any function in this util may change at any point in time
"""
from pathlib import Path

import benchexec.tools.template
from benchexec.tools.template import UnsupportedFeatureException

# Defining constants for data model.
ILP32 = "ILP32"
LP64 = "LP64"


def get_data_model_from_task(task, param_dict):
    """
    This function tries to extract tool parameter for data model
    depending on the data model in the task.
    @param task: An instance of of class Task, e.g., with the input files
    @param param_dict: Dictionary mapping data model to the tool param value
    """
    if isinstance(task.options, dict) and task.options.get("language") == "C":
        data_model = task.options.get("data_model")
        if data_model:
            try:
                return param_dict[data_model]
            except KeyError:
                raise benchexec.tools.template.UnsupportedFeatureException(
                    f"Unsupported data_model '{data_model}' defined for task '{task}'"
                )
    return None


def _partition_input_files(task):
    """
    This function partitions the input files into witness and other files.
    The distinction is based on the file name of the witness file, which
    is identified by the option "witness" in the task options.

    @param task: An instance of a task
    @return: Tuple of witness files and other files
    """
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
    """
    This function returns the witness input files from the task.
    They are identified by the option "witness" in the task options.

    @param task: An instance of a task
    @return: List of witness files
    """
    witness_files, _ = _partition_input_files(task)
    return witness_files


def get_unique_witness(task):
    """
    This function returns the unique witness file from the task.
    It raises an exception if there are multiple witness files.
    The witness file is identified by the option "witness" in the task options.

    @param task: An instance of a task
    @return: Unique witness file
    """
    witness_files = get_witness_input_files(task)
    if len(witness_files) > 1:
        raise UnsupportedFeatureException(
            "Tool does not support tasks with more than one witness file"
        )
    return witness_files[0]


def get_non_witness_input_files(task):
    """
    This function returns the non-witness input files from the task.
    They consist of all files which do not match the witness file name.
    The witness file is identified by the option "witness" in the task options.

    @param task: An instance of a task
    @return: List of non-witness files
    """
    _, other_files = _partition_input_files(task)
    return other_files


def get_unique_non_witness_input_files(task):
    """
    This function returns the unique non-witness file from the task.
    It raises an exception if there are multiple non-witness files.
    Non-witness files consist of all files which do not match the witness file name.
    The witness file is identified by the option "witness" in the task options.

    @param task: An instance of a task
    @return: Unique non-witness file
    """
    other_files = get_non_witness_input_files(task)
    if len(other_files) > 1:
        raise UnsupportedFeatureException(
            "Tool does not support tasks with more than one input file"
        )
    return other_files[0]


def get_witness_options(options, task, witness_options):
    """
    This function returns the additional options to handle witnesses.
    It checks if the witness is passed as an option or through the task definition.
    If the witness is passed through both, it raises an exception.

    @param options: List of existing options to see weather the witness
        has already been passed to the tool
    @param task: An instance of a task
    @param witness_options: List of options which need to be set to handle witnesses
        e.g. if the options are ["-w"], then the witness should be passed as "-w witness_file"
        to the tool

    @return: List of additional options to handle witnesses. They are constructed
        based on witness_options. For example if witness_options is ["-w"], then
        the return value will be ["-w", "witness_file"]
    """

    additional_options = []
    if isinstance(task.options, dict) and "witness" in task.options.keys():
        if not any(witness_option in options for witness_option in witness_options):
            for witness_option in witness_options:
                additional_options += [witness_option, get_unique_witness(task)]
        else:
            raise benchexec.tools.template.UnsupportedFeatureException(
                "You are passing a witness as both an option and through the task definition. "
                "Please remove one of them."
            )
    return additional_options
