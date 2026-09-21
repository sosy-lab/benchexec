# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import unittest

from benchexec.tablegenerator import Row, RunResult, filter_rows_with_differences
from benchexec.tablegenerator.columns import Column
from benchexec.tablegenerator.util import TaskId


def make_row(task_name, results):
    """Create a Row for one task from a list of (status, category) pairs,
    one pair per run set."""
    task_id = TaskId(task_name, None, None, None, None)
    columns = [Column("status")]
    return Row(
        [
            RunResult(task_id, status, category, None, None, columns, [status])
            for status, category in results
        ]
    )


class TestDiffTable(unittest.TestCase):
    def test_category_is_taken_into_account(self):
        same = make_row("same", [("true", "correct"), ("true", "correct")])
        different_category = make_row(
            "different_category",
            [("true", "correct"), ("true", "correct-unconfirmed")],
        )
        different_status = make_row(
            "different_status", [("true", "correct"), ("false", "wrong")]
        )

        diff = filter_rows_with_differences(
            [same, different_category, different_status]
        )

        self.assertEqual(diff, [different_category, different_status])
