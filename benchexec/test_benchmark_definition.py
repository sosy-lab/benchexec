# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import logging
import os
import tempfile
import unittest
from dataclasses import dataclass
from unittest.mock import patch

import yaml

import benchexec.result
from benchexec import BenchExecException, util
from benchexec.model import Benchmark

here = os.path.dirname(__file__)
base_dir = os.path.join(here, "..")
test_dir = os.path.join(base_dir, "test", "tasks")


@dataclass(frozen=True)
class DummyConfig:
    name = None
    output_path = "test"
    container = False
    timelimit = None
    walltimelimit = None
    memorylimit = None
    corelimit = None
    num_of_threads = None
    results_per_rundefinition = False
    results_per_taskset = False
    selected_run_definitions = None
    selected_sourcefile_sets = None
    description_file = None


ALL_TEST_TASKS = {
    "false_other_sub_task.yml": "other_subproperty",
    "false_sub_task.yml": "sub",
    "false_sub2_task.yml": "sub2",
    "false_task.yml": "expected_verdict: false",
    "true_task.yml": "expected_verdict: true",
    "unknown_task.yml": "",
}


def mock_expand_filename_pattern(pattern, base_dir):
    if pattern == "*.yml":
        return list(ALL_TEST_TASKS.keys()) + ["other_task.yml"]
    if pattern == "missing-file.txt":
        return []
    return [pattern]


def mock_load_task_def_file(f):
    content = util.read_file(os.path.join(test_dir, f))
    return yaml.safe_load(content)


def mock_property_create(property_file):
    assert property_file == "test.prp"
    return benchexec.result.Property("test.prp", False, "test")


class TestBenchmarkDefinition(unittest.TestCase):
    """
    Unit tests for reading benchmark definitions,
    testing mostly the classes from benchexec.model.
    """

    @patch("benchexec.model.load_task_definition_file", new=mock_load_task_def_file)
    @patch("benchexec.result.Property.create", new=mock_property_create)
    @patch("benchexec.util.expand_filename_pattern", new=mock_expand_filename_pattern)
    @patch("os.path.samefile", new=lambda a, b: a == b)
    def parse_benchmark_definition(self, content):
        with tempfile.NamedTemporaryFile(
            prefix="BenchExec_test_benchmark_definition_", suffix=".xml", mode="w+"
        ) as temp:
            temp.write(content)
            temp.flush()

            # Because we mocked everything that accesses the file system,
            # we can parse the benchmark definition although task files do not exist.
            return Benchmark(temp.name, DummyConfig(), util.read_local_time())

    def check_task_filter(self, filter_attr, expected):
        # The following three benchmark definitions are equivalent, we check each.
        benchmark_definitions = [
            """
            <benchmark tool="dummy">
              <propertyfile {}>test.prp</propertyfile>
              <tasks><include>*.yml</include></tasks>
              <rundefinition/>
            </benchmark>
            """,
            """
            <benchmark tool="dummy">
              <tasks>
                <propertyfile {}>test.prp</propertyfile>
                <include>*.yml</include>
              </tasks>
              <rundefinition/>
            </benchmark>
            """,
            """
            <benchmark tool="dummy">
              <tasks>
                <include>*.yml</include>
              </tasks>
              <rundefinition>
                <propertyfile {}>test.prp</propertyfile>
              </rundefinition>
            </benchmark>
            """,
        ]

        for bench_def in benchmark_definitions:
            benchmark = self.parse_benchmark_definition(bench_def.format(filter_attr))
            run_ids = [run.identifier for run in benchmark.run_sets[0].runs]
            self.assertListEqual(run_ids, sorted(expected))

    def test_expected_verdict_no_filter(self):
        self.check_task_filter("", ALL_TEST_TASKS.keys())

    def test_expected_verdict_true_filter(self):
        self.check_task_filter('expectedverdict="true"', ["true_task.yml"])

    def test_expected_verdict_false_filter(self):
        false_tasks = [f for f in ALL_TEST_TASKS if f.startswith("false")]
        self.check_task_filter('expectedverdict="false"', false_tasks)

    def test_expected_verdict_false_subproperty_filter(self):
        self.check_task_filter('expectedverdict="false(sub)"', ["false_sub_task.yml"])

    def test_expected_verdict_unknown_filter(self):
        self.check_task_filter('expectedverdict="unknown"', ["unknown_task.yml"])

    def test_expected_verdict_false_subproperties_filter(self):
        benchmark_definition = """
            <benchmark tool="dummy">
              <tasks>
                <propertyfile expectedverdict="false(sub)">test.prp</propertyfile>
                <include>*.yml</include>
              </tasks>
              <tasks>
                <propertyfile expectedverdict="false(sub2)">test.prp</propertyfile>
                <include>*.yml</include>
              </tasks>
              <rundefinition/>
            </benchmark>
            """
        benchmark = self.parse_benchmark_definition(benchmark_definition)
        run_ids = [run.identifier for run in benchmark.run_sets[0].runs]
        self.assertListEqual(run_ids, ["false_sub_task.yml", "false_sub2_task.yml"])

    def single_task_benchmark_definition(self, requiredfiles_tag):
        return f"""
            <benchmark tool="dummy">
              <propertyfile>test.prp</propertyfile>
              <rundefinition>
                {requiredfiles_tag}
                <tasks><include>true_task.yml</include></tasks>
              </rundefinition>
            </benchmark>
            """

    def test_requiredfiles_default_mode_missing_file_keeps_run(self):
        benchmark_definition = self.single_task_benchmark_definition(
            "<requiredfiles>missing-file.txt</requiredfiles>"
        )
        with self.assertLogs(level="WARNING") as log:
            benchmark = self.parse_benchmark_definition(benchmark_definition)
        run_ids = [run.identifier for run in benchmark.run_sets[0].runs]
        self.assertListEqual(run_ids, ["true_task.yml"])
        self.assertTrue(
            any("did not match any file" in message for message in log.output)
        )

    def test_requiredfiles_warn_mode_missing_file_keeps_run(self):
        benchmark_definition = self.single_task_benchmark_definition(
            '<requiredfiles ifmissing="warn">missing-file.txt</requiredfiles>'
        )
        with self.assertLogs(level="WARNING") as log:
            benchmark = self.parse_benchmark_definition(benchmark_definition)
        run_ids = [run.identifier for run in benchmark.run_sets[0].runs]
        self.assertListEqual(run_ids, ["true_task.yml"])
        self.assertTrue(
            any("did not match any file" in message for message in log.output)
        )

    def test_requiredfiles_ignore_mode_missing_file_keeps_run_silently(self):
        benchmark_definition = self.single_task_benchmark_definition(
            '<requiredfiles ifmissing="ignore">missing-file.txt</requiredfiles>'
        )
        with self.assertLogs(level="DEBUG") as log:
            # emit one debug message ourselves so assertLogs does not fail
            # if <requiredfiles ifmissing="ignore"> stays completely silent
            logging.debug("start of test_requiredfiles_ignore_mode test")
            benchmark = self.parse_benchmark_definition(benchmark_definition)
        run_ids = [run.identifier for run in benchmark.run_sets[0].runs]
        self.assertListEqual(run_ids, ["true_task.yml"])
        self.assertFalse(
            any("did not match any file" in message for message in log.output)
        )

    def test_requiredfiles_fail_mode_missing_file_raises(self):
        benchmark_definition = self.single_task_benchmark_definition(
            '<requiredfiles ifmissing="fail">missing-file.txt</requiredfiles>'
        )
        with self.assertRaises(BenchExecException):
            self.parse_benchmark_definition(benchmark_definition)

    def test_requiredfiles_skip_mode_missing_file_skips_run(self):
        benchmark_definition = self.single_task_benchmark_definition(
            '<requiredfiles ifmissing="skip-run">missing-file.txt</requiredfiles>'
        )
        with self.assertLogs(level="WARNING") as log:
            benchmark = self.parse_benchmark_definition(benchmark_definition)
        run_ids = [run.identifier for run in benchmark.run_sets[0].runs]
        self.assertListEqual(run_ids, [])
        matching_messages = [message for message in log.output if "Skipped" in message]
        self.assertEqual(len(matching_messages), 1)
        self.assertIn("1 run", matching_messages[0])

    def test_requiredfiles_skip_mode_matching_file_keeps_run(self):
        benchmark_definition = self.single_task_benchmark_definition(
            '<requiredfiles ifmissing="skip-run">some-existing-file.txt</requiredfiles>'
        )
        benchmark = self.parse_benchmark_definition(benchmark_definition)
        run_ids = [run.identifier for run in benchmark.run_sets[0].runs]
        self.assertListEqual(run_ids, ["true_task.yml"])
        self.assertIn(
            "some-existing-file.txt", benchmark.run_sets[0].runs[0].required_files
        )

    def test_requiredfiles_invalid_mode_raises(self):
        benchmark_definition = self.single_task_benchmark_definition(
            '<requiredfiles ifmissing="bogus">missing-file.txt</requiredfiles>'
        )
        with self.assertRaises(BenchExecException):
            self.parse_benchmark_definition(benchmark_definition)

    def test_requiredfiles_skip_mode_skips_only_runs_with_missing_files(self):
        # checking the arithmetics into a bit more detail
        benchmark_definition = """
            <benchmark tool="dummy">
              <propertyfile>test.prp</propertyfile>
              <rundefinition>
                <tasks>
                  <requiredfiles ifmissing="skip-run">missing-file.txt</requiredfiles>
                  <include>*.yml</include>
                </tasks>
                <tasks>
                    <requiredfiles ifmissing="skip-run">missing-file.txt</requiredfiles>
                    <include>*.yml</include>
                </tasks>
                <tasks>
                    <requiredfiles ifmissing="skip-run">missing-file.txt</requiredfiles>
                    <include>*.yml</include>
                    </tasks>
                <tasks>
                    <requiredfiles ifmissing="skip-run">missing-file.txt</requiredfiles>
                    <include>*.yml</include>
                </tasks>
                <tasks>
                  <requiredfiles ifmissing="skip-run">present-file.txt</requiredfiles>
                  <include>true_task.yml</include>
                </tasks>
              </rundefinition>
            </benchmark>
            """
        # each of the two "*.yml"-including <tasks> blocks resolves (via the mock) to
        # all of ALL_TEST_TASKS plus "other_task.yml" - all of those get skipped,
        # and the single summary message must report both blocks combined
        expected_skipped_count = 4 * len(
            mock_expand_filename_pattern("*.yml", base_dir)
        )
        with self.assertLogs(level="WARNING") as log:
            benchmark = self.parse_benchmark_definition(benchmark_definition)
        run_ids = [run.identifier for run in benchmark.run_sets[0].runs]
        self.assertListEqual(run_ids, ["true_task.yml"])
        matching_messages = [m for m in log.output if "Skipped" in m]
        # exactly one summary message for the whole benchmark, not one per <tasks> block
        self.assertEqual(len(matching_messages), 1)
        self.assertIn(f"Skipped {expected_skipped_count} run(s)", matching_messages[0])
