# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2026 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import collections
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import yaml

from benchexec import util
from benchexec.model import Benchmark
from contrib.vcloud import benchmarkclient_executor

here = os.path.dirname(__file__)
TEST_TASKS_DIR = os.path.join(here, "..", "..", "test", "tasks")

VCloudConfig = collections.namedtuple(
    "VCloudConfig",
    [
        "name",
        "output_path",
        "container",
        "timelimit",
        "walltimelimit",
        "memorylimit",
        "corelimit",
        "num_of_threads",
        "results_per_rundefinition",
        "results_per_taskset",
        "selected_run_definitions",
        "selected_sourcefile_sets",
        "description_file",
        "cloudPriority",
        "additional_files",
        "cpu_model",
    ],
)

DEFAULT_CONFIG = VCloudConfig(
    name=None,
    output_path="test/",
    container=False,
    timelimit=None,
    walltimelimit=None,
    memorylimit=None,
    corelimit=None,
    num_of_threads=None,
    results_per_rundefinition=False,
    results_per_taskset=False,
    selected_run_definitions=None,
    selected_sourcefile_sets=None,
    description_file=None,
    cloudPriority=None,
    additional_files=[],
    cpu_model=None,
)


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
    Tests for benchmarkclient_executor.getCloudInput() to check that the runs and required files generated for
    the cloud are correct.
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.tool_file = os.path.join(TEST_TASKS_DIR, "test.sh")
        open(self.tool_file, "w").close()

    def tearDown(self):
        os.remove(self.tool_file)

    def _make_mock_tool(self, working_directory=None):
        tool = MagicMock()
        tool.name.return_value = "MockTool"
        tool.working_directory.return_value = working_directory or self.tmpdir
        tool.program_files.return_value = {self.tool_file}
        tool.cmdline.return_value = ["mock-tool"]
        tool.environment.return_value = {}
        return tool

    def _parse_benchmark(self, xml_content, config=DEFAULT_CONFIG, tool=None):
        mock_tool = tool or self._make_mock_tool()
        with patch(
            "benchexec.model.load_tool_info",
            return_value=("benchexec.tools.mock", mock_tool),
        ):
            with tempfile.NamedTemporaryFile(
                suffix=".xml",
                mode="w",
                delete=False,
                dir=TEST_TASKS_DIR,
            ) as f:
                f.write(xml_content)
                xml_path = f.name
            try:
                benchmark = Benchmark(xml_path, config, util.read_local_time())
            finally:
                os.remove(xml_path)
        benchmark.executable = self.tool_file
        return benchmark

    def _get_cloud_input(self, xml_content, config=DEFAULT_CONFIG, tool=None):
        benchmark = self._parse_benchmark(xml_content, config, tool=tool)
        yaml_str, n_runs = benchmarkclient_executor.getCloudInput(benchmark)
        return yaml.safe_load(yaml_str), n_runs

    def test_minimal(self):
        # one task with no inputs, no result files, only cputime_hard set
        cloud_input, n_runs = self._get_cloud_input("""
            <benchmark tool="dummy" hardtimelimit="30">
              <rundefinition>
                <tasks><withoutfile>task1</withoutfile></tasks>
              </rundefinition>
            </benchmark>
        """)
        self.assertEqual(cloud_input["formatVersion"], "1.0")
        self.assertCountEqual(cloud_input["files"], ["test.sh"])

        self.assertEqual(cloud_input["limits"]["cputime_hard_s"], 30)
        self.assertNotIn("walltime_hard_s", cloud_input["limits"])
        self.assertNotIn("memory_b", cloud_input["limits"])
        self.assertNotIn("cores", cloud_input["limits"])
        self.assertNotIn("priority", cloud_input)
        self.assertIsNone(cloud_input["requirements"]["cores"])
        self.assertIsNone(cloud_input["requirements"]["memory_b"])
        self.assertNotIn("cpumodels", cloud_input["requirements"])
        self.assertEqual(cloud_input["resultFilePatterns"], ["."])

        self.assertEqual(n_runs, 1)
        self.assertEqual(len(cloud_input["runs"]), 1)

    def test_input_files(self):
        extra_file = os.path.join(TEST_TASKS_DIR, "other.prp")
        config = DEFAULT_CONFIG._replace(additional_files=[extra_file])
        cloud_input, _ = self._get_cloud_input(
            """
            <benchmark tool="dummy" hardtimelimit="30">
              <rundefinition>
                <tasks><withoutfile>task1</withoutfile></tasks>
              </rundefinition>
            </benchmark>
            """,
            config=config,
        )

        self.assertTrue(os.path.isdir(cloud_input["basedir"]))
        self.assertTrue(
            os.path.isdir(os.path.join(cloud_input["basedir"], cloud_input["execdir"]))
        )
        self.assertCountEqual(cloud_input["files"], ["test.sh", "other.prp"])

    def test_invalid_additional_file_exits(self):
        config = DEFAULT_CONFIG._replace(additional_files=["/no/such/file"])
        with self.assertRaises(SystemExit):
            self._get_cloud_input(
                """
                <benchmark tool="dummy" hardtimelimit="30">
                  <rundefinition>
                    <tasks><withoutfile>task1</withoutfile></tasks>
                  </rundefinition>
                </benchmark>
                """,
                config=config,
            )

    def test_invalid_working_directory_exits(self):
        tool = self._make_mock_tool(working_directory="/no/such/directory")
        with self.assertRaises(SystemExit):
            self._get_cloud_input(
                """
                <benchmark tool="dummy" hardtimelimit="30">
                  <rundefinition>
                    <tasks><withoutfile>task1</withoutfile></tasks>
                  </rundefinition>
                </benchmark>
                """,
                tool=tool,
            )

    def test_single_rundefinition_multiple_tasks_with_input(self):
        cloud_input, n_runs = self._get_cloud_input("""
            <benchmark tool="dummy" hardtimelimit="30">
              <propertyfile>test.prp</propertyfile>
              <rundefinition>
                <tasks>
                  <include>true_task.yml</include>
                  <include>false_task.yml</include>
                </tasks>
              </rundefinition>
            </benchmark>
        """)
        expected_runs = [
            {
                "logfile": "true_task.yml.log",
                "command": ["mock-tool"],
                "files": ["true_task.yml", "test.prp"],
            },
            {
                "logfile": "false_task.yml.log",
                "command": ["mock-tool"],
                "files": ["false_task.yml", "test.prp"],
            },
        ]
        self.assertEqual(n_runs, len(expected_runs))
        self.assertCountEqual(cloud_input["runs"], expected_runs)

    def test_single_run_definition_multiple_tasks_without_inputs(self):
        cloud_input, n_runs = self._get_cloud_input("""
            <benchmark tool="dummy" hardtimelimit="30">
              <rundefinition>
                <tasks>
                  <withoutfile>task1</withoutfile>
                  <withoutfile>task2</withoutfile>
                </tasks>
                <tasks>
                  <withoutfile>task3</withoutfile>
                </tasks>
              </rundefinition>
            </benchmark>
        """)
        self.assertEqual(n_runs, 3)
        self.assertCountEqual(
            cloud_input["runs"],
            [
                {"logfile": "task1.log", "command": ["mock-tool"]},
                {"logfile": "task2.log", "command": ["mock-tool"]},
                {"logfile": "task3.log", "command": ["mock-tool"]},
            ],
        )

    def test_multiple_rundefinitions_multiple_tasks_without_inputs(self):
        cloud_input, n_runs = self._get_cloud_input("""
            <benchmark tool="dummy" hardtimelimit="30">
              <rundefinition name="run1">
                <tasks><withoutfile>task1</withoutfile></tasks>
              </rundefinition>
              <rundefinition name="run2">
                <tasks><withoutfile>task2</withoutfile></tasks>
              </rundefinition>
            </benchmark>
        """)
        # All run definitions should be flattened for the cloud input file
        self.assertEqual(n_runs, 2)
        self.assertCountEqual(
            cloud_input["runs"],
            [
                {"logfile": "run1.task1.log", "command": ["mock-tool"]},
                {"logfile": "run2.task2.log", "command": ["mock-tool"]},
            ],
        )

    def test_unselected_rundefinition_is_excluded(self):
        config = DEFAULT_CONFIG._replace(selected_run_definitions=["run1"])
        cloud_input, n_runs = self._get_cloud_input(
            """
            <benchmark tool="dummy" hardtimelimit="30">
              <rundefinition name="run1">
                <tasks><withoutfile>task1</withoutfile></tasks>
              </rundefinition>
              <rundefinition name="run2">
                <tasks><withoutfile>task2</withoutfile></tasks>
              </rundefinition>
            </benchmark>
            """,
            config=config,
        )
        self.assertEqual(n_runs, 1)
        self.assertCountEqual(
            cloud_input["runs"],
            [{"logfile": "run1.task1.log", "command": ["mock-tool"]}],
        )

    def test_no_matching_rundefinition_selected_exits(self):
        config = DEFAULT_CONFIG._replace(selected_run_definitions=["nonexistent"])
        with self.assertRaises(SystemExit):
            self._get_cloud_input(
                """
                <benchmark tool="dummy" hardtimelimit="30">
                  <rundefinition name="run1">
                    <tasks><withoutfile>task1</withoutfile></tasks>
                  </rundefinition>
                </benchmark>
                """,
                config=config,
            )

    def test_limits_and_requirements_set(self):
        cloud_input, _ = self._get_cloud_input("""
            <benchmark tool="dummy" hardtimelimit="60" walltimelimit="120"
                       memlimit="4 GB" cpuCores="2">
              <require cpuCores="1" memory="4 GB" cpuModel="Intel"/>
              <rundefinition>
                <tasks><withoutfile>task1</withoutfile></tasks>
              </rundefinition>
            </benchmark>
        """)

        self.assertEqual(cloud_input["limits"]["cputime_hard_s"], 60)
        self.assertEqual(cloud_input["limits"]["walltime_hard_s"], 120)

        self.assertEqual(cloud_input["limits"]["memory_b"], 4_000_000_000)
        self.assertEqual(cloud_input["limits"]["cores"], 2)
        self.assertEqual(cloud_input["requirements"]["cores"], 1)
        self.assertEqual(cloud_input["requirements"]["memory_b"], 4_000_000_000)
        self.assertEqual(cloud_input["requirements"]["cpumodels"], "Intel")

    def test_result_file_patterns_set(self):
        cloud_input, _ = self._get_cloud_input("""
            <benchmark tool="dummy" hardtimelimit="30">
              <resultfiles>*.log</resultfiles>
              <rundefinition>
                <tasks><withoutfile>task1</withoutfile></tasks>
              </rundefinition>
            </benchmark>
        """)
        self.assertEqual(cloud_input["resultFilePatterns"], ["*.log"])

    def test_result_file_patterns_empty(self):
        cloud_input, _ = self._get_cloud_input("""
            <benchmark tool="dummy" hardtimelimit="30">
              <resultfiles></resultfiles>
              <rundefinition>
                <tasks><withoutfile>task1</withoutfile></tasks>
              </rundefinition>
            </benchmark>
        """)
        self.assertEqual(cloud_input["resultFilePatterns"], [])

    def test_priority_from_config(self):
        config = DEFAULT_CONFIG._replace(cloudPriority="HIGH")
        cloud_input, _ = self._get_cloud_input(
            """
            <benchmark tool="dummy" hardtimelimit="30">
              <rundefinition>
                <tasks><withoutfile>task1</withoutfile></tasks>
              </rundefinition>
            </benchmark>
            """,
            config=config,
        )
        self.assertEqual(cloud_input["priority"], "HIGH")


if __name__ == "__main__":
    unittest.main()
