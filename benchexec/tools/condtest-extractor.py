# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.tools.condtest as condtest


class Tool(condtest.Tool):
    """
    This tool extracts the goals from generated test cases.
    """

    _exec_path = "bin/extractor/test_executor"

    def name(self):
        return "CondTest Extractor"
