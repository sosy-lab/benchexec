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

import benchexec.tools.template

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
