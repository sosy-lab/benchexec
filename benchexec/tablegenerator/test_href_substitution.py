# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2026 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import unittest
from dataclasses import dataclass

from benchexec.tablegenerator import htmltable
from benchexec.tablegenerator.util import TaskId


def DummyTaskId(name):
    return TaskId(name, None, None, None, None)


@dataclass(frozen=True)
class DummyRunResult:
    task_id: TaskId
    log_file: str | None = None


class TestHrefSubstitution(unittest.TestCase):
    def test_create_link_with_value_substitution(self):
        href = "http://example.com/${value}"
        base_dir = "."
        value = "test-value"
        run_result = DummyRunResult(DummyTaskId("task1"))

        # Test basic substitution
        link = htmltable._create_link(href, base_dir, runResult=run_result, value=value)
        self.assertEqual(link, "http://example.com/test-value")

    def test_create_link_with_value_substitution_and_other_vars(self):
        href = "http://example.com/${inputfile_name}?v=${value}"
        base_dir = "."
        value = "123"
        run_result = DummyRunResult(DummyTaskId("dir/task1.c"))

        link = htmltable._create_link(href, base_dir, runResult=run_result, value=value)
        self.assertEqual(link, "http://example.com/task1.c?v=123")

    def test_create_link_backward_compatibility(self):
        href = "http://example.com/static"
        base_dir = "."

        link = htmltable._create_link(href, base_dir)
        self.assertEqual(link, "http://example.com/static")
