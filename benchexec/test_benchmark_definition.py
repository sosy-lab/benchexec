# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import collections
import os
import tempfile
import pytest
from unittest.mock import patch
import yaml

from benchexec.model import Benchmark
import benchexec.result
import benchexec.util as util

here = os.path.dirname(__file__)
base_dir = os.path.join(here, "..")
test_dir = os.path.join(base_dir, "test", "tasks")

DummyConfig = collections.namedtuple(
    "DummyConfig",
    [
        "name",
        "output_path",
        "container",
        "timelimit",
        "walltimelimit",
        "memorylimit",
        "corelimit",
        "num_of_threads",
        "selected_run_definitions",
        "selected_sourcefile_sets",
        "description_file",
    ],
)(None, "test", False, None, None, None, None, None, None, None, None)

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
    return [pattern]


def mock_load_task_def_file(f):
    content = util.read_file(os.path.join(test_dir, f))
    return yaml.safe_load(content)


def mock_property_create(property_file):
    assert property_file == "test.prp"
    return benchexec.result.Property("test.prp", False, "test")


@pytest.fixture(autouse=True)
def mock_benchmark_fixture(request):
    patchers = [
        patch("benchexec.model.load_task_definition_file", new=mock_load_task_def_file),
        patch("benchexec.result.Property.create", new=mock_property_create),
        patch("benchexec.util.expand_filename_pattern", new=mock_expand_filename_pattern),
        patch("os.path.samefile", new=lambda a, b: a == b)
    ]
    for patcher in patchers:
        patcher.start()
        request.addfinalizer(patcher.stop)


def parse_benchmark_definition(content):
    with tempfile.NamedTemporaryFile(
        prefix="BenchExec_test_benchmark_definition_", suffix=".xml", mode="w+"
    ) as temp:
        temp.write(content)
        temp.flush()

        # Because we mocked everything that accesses the file system,
        # we can parse the benchmark definition although task files do not exist.
        return Benchmark(temp.name, DummyConfig, util.read_local_time())


def check_task_filter(filter_attr, expected):
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
        benchmark = parse_benchmark_definition(bench_def.format(filter_attr))
        run_ids = [run.identifier for run in benchmark.run_sets[0].runs]
        assert run_ids == sorted(expected)


def test_expected_verdict_no_filter():
    check_task_filter("", ALL_TEST_TASKS.keys())


def test_expected_verdict_true_filter():
    check_task_filter('expectedverdict="true"', ["true_task.yml"])


def test_expected_verdict_false_filter():
    false_tasks = [f for f in ALL_TEST_TASKS.keys() if f.startswith("false")]
    check_task_filter('expectedverdict="false"', false_tasks)


def test_expected_verdict_false_subproperty_filter():
    check_task_filter('expectedverdict="false(sub)"', ["false_sub_task.yml"])


def test_expected_verdict_unknown_filter():
    check_task_filter('expectedverdict="unknown"', ["unknown_task.yml"])


def test_expected_verdict_false_subproperties_filter():
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
    benchmark = parse_benchmark_definition(benchmark_definition)
    run_ids = [run.identifier for run in benchmark.run_sets[0].runs]
    assert run_ids == ["false_sub_task.yml", "false_sub2_task.yml"]