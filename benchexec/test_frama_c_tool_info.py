# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import unittest

from benchexec import tooladapter
from benchexec.tools.template import BaseTool2

# The module name is not a valid Python identifier.
frama_c = __import__("benchexec.tools.frama-c", fromlist=["Tool"])


class TestFramaCToolInfo(unittest.TestCase):
    def setUp(self):
        self.tool = tooladapter.adapt_to_current_version(frama_c.Tool())

    def test_cmdline_without_then(self):
        task = BaseTool2.Task.with_files(["a.c", "b.c"])
        rlimits = BaseTool2.ResourceLimits()
        self.assertEqual(
            self.tool.cmdline("frama-c", ["-eva"], task, rlimits),
            ["frama-c", "-eva", "a.c", "b.c"],
        )

    def test_cmdline_task_files_before_first_then(self):
        task = BaseTool2.Task.with_files(["a.c"])
        rlimits = BaseTool2.ResourceLimits()
        self.assertEqual(
            self.tool.cmdline(
                "frama-c", ["-eva", "-then", "-report", "-then-last"], task, rlimits
            ),
            ["frama-c", "-eva", "a.c", "-then", "-report", "-then-last"],
        )
