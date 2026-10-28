# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import os
import stat
import tempfile
import unittest

from benchexec import tooladapter
from benchexec.tools.template import BaseTool2, ToolNotFoundException

# The module name is not a valid Python identifier.
frama_c = __import__("benchexec.tools.frama-c", fromlist=["Tool"])


class TestFramaCToolInfo(unittest.TestCase):
    def setUp(self):
        self.tool = tooladapter.adapt_to_current_version(frama_c.Tool())

    def test_executable_in_tool_directory(self):
        with tempfile.TemporaryDirectory() as tool_dir:
            os.mkdir(os.path.join(tool_dir, "bin"))
            expected = os.path.join(tool_dir, "bin", "frama-c")
            with open(expected, "w") as f:
                f.write("#!/bin/sh\n")
            os.chmod(expected, stat.S_IRWXU)

            locator = BaseTool2.ToolLocator(tool_directory=tool_dir)
            self.assertEqual(self.tool.executable(locator), expected)

    def test_executable_missing_in_tool_directory(self):
        with tempfile.TemporaryDirectory() as tool_dir:
            locator = BaseTool2.ToolLocator(tool_directory=tool_dir)
            with self.assertRaisesRegex(
                ToolNotFoundException, "Could not find executable 'frama-c'"
            ):
                self.tool.executable(locator)

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
