# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.tools.condtest as condtest


class Tool(condtest.Tool):
    """
    This tool prunes the input file by removing any goal targets not provided in the input.
    """

    _exec_path = "bin/reducer/pruner"

    def name(self):
        return "CondTest Pruner"
