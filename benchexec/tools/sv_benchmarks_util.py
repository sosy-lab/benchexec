# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

"""
This module contains some useful functions related to tasks in the sv-benchmarks
repository: https://github.com/sosy-lab/sv-benchmarks
"""

import benchexec.tools.template


def get_data_model_from_task(task, data_models):
    if isinstance(task.options, dict) and task.options.get("language") == "C":
        data_model = task.options.get("data_model")
        if data_model:
            data_model_option = data_models.get(data_model)
            if data_model_option:
                return data_model_option
            else:
                raise benchexec.tools.template.UnsupportedFeatureException(
                    "Unsupported data_model '{}' defined for task '{}'".format(
                        data_model, task
                    )
                )
    return None
