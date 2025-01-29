# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.tools.condtest as condtest


class Tool(condtest.Tool):
    """
    This tool instruments the test criteria in the C file, such that a verifier
    can be used on it.
    """

    _exec_path = "bin/instrumenter/instrumenter"

    def name(self):
        return "CondTest Instrumenter"
