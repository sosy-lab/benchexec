import os
import unittest
from benchexec.tablegenerator import htmltable
from benchexec.tablegenerator.columns import Column


class TestHrefSubstitution(unittest.TestCase):
    def test_create_link_with_value_substitution(self):
        href = "http://example.com/${value}"
        base_dir = "."
        value = "test-value"

        # We need a dummy runResult for _create_link to work if it tries to get source_file
        # or we can pass None if we handle it.
        # Looking at _create_link, it uses runResult to get source_file.

        class DummyTaskId:
            def __init__(self, name):
                self.name = name

        class DummyRunResult:
            def __init__(self, task_name, log_file=None):
                self.task_id = DummyTaskId(task_name)
                self.log_file = log_file

            def __getitem__(self, key):
                return getattr(self, key)

        run_result = DummyRunResult("task1")

        # Test basic substitution
        link = htmltable._create_link(href, base_dir, runResult=run_result, value=value)
        self.assertEqual(link, "http://example.com/test-value")

    def test_create_link_with_value_substitution_and_other_vars(self):
        href = "http://example.com/${inputfile_name}?v=${value}"
        base_dir = "."
        value = "123"

        class DummyTaskId:
            def __init__(self, name):
                self.name = name

        class DummyRunResult:
            def __init__(self, task_name, log_file=None):
                self.task_id = DummyTaskId(task_name)
                self.log_file = log_file

        run_result = DummyRunResult("dir/task1.c")

        link = htmltable._create_link(href, base_dir, runResult=run_result, value=value)
        self.assertEqual(link, "http://example.com/task1.c?v=123")

    def test_create_link_backward_compatibility(self):
        href = "http://example.com/static"
        base_dir = "."

        link = htmltable._create_link(href, base_dir)
        self.assertEqual(link, "http://example.com/static")


if __name__ == "__main__":
    unittest.main()
