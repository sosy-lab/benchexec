# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2026 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import os
import unittest
from dataclasses import dataclass, field
from unittest.mock import MagicMock, patch

import yaml

from benchexec import util
from benchexec.model import Benchmark
from contrib.vcloud import benchmarkclient_executor

here = os.path.dirname(__file__)
REPO_ROOT = os.path.join(here, "..", "..")
TEST_TASKS_DIR = os.path.join(REPO_ROOT, "test", "tasks")

INPUT_DIR = os.path.join(here, "test_integration")
EXPECTED_DIR = os.path.join(INPUT_DIR, "expected")

TOOL_DIR = os.path.join(INPUT_DIR, "tool")
MOCK_TOOL_FILE = os.path.join(TOOL_DIR, "mock_tool.sh")

# Set to True to let the tests overwrite the expected YAML files with the actual result
# from parsing the test-integration/*.xml files using benchmarkclient_executor.getCloudInput
# Use this to update expected files if necessary. Do not commit this flag set to True!
OVERWRITE_MODE = False


@dataclass(frozen=True)
class VCloudConfig:
    name: str | None = None
    output_path: str = "test/"
    container: bool = False
    timelimit: int | None = None
    walltimelimit: int | None = None
    memorylimit: int | None = None
    corelimit: int | None = None
    num_of_threads: int | None = None
    results_per_rundefinition: bool = False
    results_per_taskset: bool = False
    selected_run_definitions: list | None = None
    selected_sourcefile_sets: list | None = None
    description_file: str | None = None
    cloudPriority: str | None = None
    additional_files: list = field(default_factory=list)
    cpu_model: str | None = None


DEFAULT_CONFIG = VCloudConfig()


class TestInit(unittest.TestCase):
    """Tests for benchmarkclient_executor.init(), which validates
    the configuration before a cloud run is started."""

    def test_missing_cputime_hard_limit_exits(self):
        config = MagicMock(reprocessResults=False)
        benchmark = MagicMock()
        benchmark.rlimits.cputime_hard = None
        with self.assertRaises(SystemExit):
            benchmarkclient_executor.init(config, benchmark)

    def test_unsupported_environment_configuration_exits(self):
        config = MagicMock(
            reprocessResults=False, containerImage=None, tool_directory=None
        )
        benchmark = MagicMock()
        benchmark.rlimits.cputime_hard = 30
        benchmark.environment.return_value = {"keepEnv": {"PATH": "/usr/bin"}}
        with self.assertRaises(SystemExit):
            benchmarkclient_executor.init(config, benchmark)


class TestCloudInput(unittest.TestCase):
    """
    Tests for benchmarkclient_executor.getCloudInput() to check that the runs and
    required files generated for the cloud are correct.
    """

    def _make_mock_tool(self, working_directory=None):
        tool = MagicMock()
        tool.name.return_value = "MockTool"
        tool.working_directory.return_value = working_directory or TOOL_DIR
        tool.program_files.return_value = {MOCK_TOOL_FILE}
        tool.cmdline.return_value = ["mock-tool"]
        tool.environment.return_value = {}
        return tool

    def _parse_benchmark(self, input_file, config=DEFAULT_CONFIG, tool=None):
        mock_tool = tool or self._make_mock_tool()
        with patch(
            "benchexec.model.load_tool_info",
            return_value=("benchexec.tools.mock", mock_tool),
        ):
            benchmark = Benchmark(
                os.path.join(INPUT_DIR, input_file), config, util.read_local_time()
            )
        benchmark.executable = MOCK_TOOL_FILE
        return benchmark

    def _get_cloud_input(self, input_file, config=DEFAULT_CONFIG, tool=None):
        benchmark = self._parse_benchmark(input_file, config, tool=tool)
        return benchmarkclient_executor.getCloudInput(benchmark)

    def _normalize_cloud_input(self, cloud_input):
        normalized = dict(cloud_input)
        # The top-level "files" list comes from a set internally, so its
        # order is not guaranteed.
        normalized["files"] = sorted(normalized["files"])
        # We always assume the expected input YAML files are relative to REPO_ROOT
        normalized["basedir"] = os.path.relpath(cloud_input["basedir"], REPO_ROOT)
        return normalized

    def _overwrite_expected(self, actual, expected_file_name):
        expected_file = os.path.join(EXPECTED_DIR, expected_file_name)
        util.write_file(
            yaml.dump(
                actual, default_flow_style=False, sort_keys=True, allow_unicode=True
            ),
            expected_file,
        )

    def assertCloudInputMatchesExpected(self, cloud_input, expected_file_name):
        actual = self._normalize_cloud_input(cloud_input)

        if OVERWRITE_MODE:
            self._overwrite_expected(actual, expected_file_name)
            return

        expected_file = os.path.join(EXPECTED_DIR, expected_file_name)
        expected = yaml.safe_load(util.read_file(expected_file))
        self.assertEqual(actual, expected)

    def test_minimal(self):
        cloud_input = self._get_cloud_input("minimal.xml")
        self.assertEqual(len(cloud_input["runs"]), 1)
        self.assertCloudInputMatchesExpected(cloud_input, "minimal.yml")

    def test_input_files_and_dirs(self):
        extra_file = os.path.join(TEST_TASKS_DIR, "other.prp")
        config = VCloudConfig(additional_files=[extra_file])
        cloud_input = self._get_cloud_input("input_files_and_dirs.xml", config=config)

        self.assertTrue(os.path.isdir(cloud_input["basedir"]))
        self.assertTrue(
            os.path.isdir(os.path.join(cloud_input["basedir"], cloud_input["execdir"]))
        )
        self.assertCloudInputMatchesExpected(cloud_input, "input_files_and_dirs.yml")

    def test_invalid_additional_file_exits(self):
        config = VCloudConfig(additional_files=["/no/such/file"])
        with self.assertRaises(SystemExit):
            self._get_cloud_input("minimal.xml", config=config)

    def test_invalid_working_directory_exits(self):
        tool = self._make_mock_tool(working_directory="/no/such/directory")
        with self.assertRaises(SystemExit):
            self._get_cloud_input("minimal.xml", tool=tool)

    def test_single_rundefinition_multiple_tasks_with_input(self):
        cloud_input = self._get_cloud_input(
            "single_rundefinition_multiple_tasks_with_input.xml"
        )
        self.assertEqual(len(cloud_input["runs"]), 2)
        self.assertCloudInputMatchesExpected(
            cloud_input, "single_rundefinition_multiple_tasks_with_input.yml"
        )

    def test_single_run_definition_multiple_tasks_without_inputs(self):
        cloud_input = self._get_cloud_input(
            "single_run_definition_multiple_tasks_without_inputs.xml"
        )
        self.assertEqual(len(cloud_input["runs"]), 3)
        self.assertCloudInputMatchesExpected(
            cloud_input, "single_run_definition_multiple_tasks_without_inputs.yml"
        )

    def test_multiple_rundefinitions_multiple_tasks_without_inputs(self):
        cloud_input = self._get_cloud_input("multiple_rundefinitions.xml")
        # All run definitions should be flattened for the cloud input file
        self.assertEqual(len(cloud_input["runs"]), 2)
        self.assertCloudInputMatchesExpected(cloud_input, "multiple_rundefinitions.yml")

    def test_unselected_rundefinition_is_excluded(self):
        config = VCloudConfig(selected_run_definitions=["run1"])
        cloud_input = self._get_cloud_input(
            "multiple_rundefinitions.xml", config=config
        )
        self.assertEqual(len(cloud_input["runs"]), 1)
        self.assertCloudInputMatchesExpected(
            cloud_input, "unselected_rundefinition_is_excluded.yml"
        )

    def test_no_matching_rundefinition_selected_exits(self):
        config = VCloudConfig(selected_run_definitions=["nonexistent"])
        with self.assertRaises(SystemExit):
            self._get_cloud_input("multiple_rundefinitions.xml", config=config)

    def test_limits_and_requirements_set(self):
        cloud_input = self._get_cloud_input("limits_and_requirements_set.xml")
        self.assertCloudInputMatchesExpected(
            cloud_input, "limits_and_requirements_set.yml"
        )

    def test_result_file_patterns_set(self):
        cloud_input = self._get_cloud_input("result_file_patterns_set.xml")
        self.assertCloudInputMatchesExpected(
            cloud_input, "result_file_patterns_set.yml"
        )

    def test_result_file_patterns_empty(self):
        cloud_input = self._get_cloud_input("result_file_patterns_empty.xml")
        self.assertCloudInputMatchesExpected(
            cloud_input, "result_file_patterns_empty.yml"
        )

    def test_priority_from_config(self):
        config = VCloudConfig(cloudPriority="HIGH")
        cloud_input = self._get_cloud_input("minimal.xml", config=config)
        self.assertCloudInputMatchesExpected(cloud_input, "priority_from_config.yml")
