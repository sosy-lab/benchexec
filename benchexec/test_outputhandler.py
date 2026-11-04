# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2025 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import os
import tempfile
import unittest
from unittest.mock import patch
from xml.etree import ElementTree

from benchexec import util
from benchexec.model import Benchmark
from benchexec.outputhandler import OutputHandler

BENCHMARK_DEFINITION = """
<benchmark tool="dummy">
  <rundefinition name="rd1">
    <tasks name="setA"><withoutfile>taskA1</withoutfile></tasks>
    <tasks name="setB"><withoutfile>taskB1</withoutfile></tasks>
  </rundefinition>
</benchmark>
"""


class DummyConfig:
    name = None
    container = False
    timelimit = None
    walltimelimit = None
    memorylimit = None
    corelimit = None
    num_of_threads = None
    selected_run_definitions = None
    selected_sourcefile_sets = None
    description_file = None
    start_time = None
    compress_results = False
    results_per_rundefinition = False
    results_per_taskset = True

    def __init__(self, output_path):
        self.output_path = output_path


class TestIncrementalTasksetFiles(unittest.TestCase):
    @patch("benchexec.outputhandler._INTERMEDIATE_WRITE_INTERVAL", 0)
    def test_taskset_files_are_written_after_each_run(self):
        with tempfile.TemporaryDirectory() as output_dir:
            config = DummyConfig(os.path.join(output_dir, ""))
            with tempfile.NamedTemporaryFile(
                suffix=".xml", mode="w+", dir=output_dir
            ) as temp:
                temp.write(BENCHMARK_DEFINITION)
                temp.flush()
                benchmark = Benchmark(temp.name, config, util.read_local_time())

            benchmark.tool_version = "1.0"
            handler = OutputHandler(benchmark, None, config)
            run_set = benchmark.run_sets[0]
            handler.output_before_run_set(run_set)

            block_a, block_b = run_set.blocks[0], run_set.blocks[1]
            file_a = run_set.block_xml_files[block_a.name]["filename"]
            file_b = run_set.block_xml_files[block_b.name]["filename"]

            # both files are empty before run finished
            self.assertEqual(self._count_runs(file_a), 0)
            self.assertEqual(self._count_runs(file_b), 0)

            self._finish_run(block_a.runs[0])
            handler.output_after_run(block_a.runs[0])

            # the result of the finished run is on disk before the benchmark ends
            self.assertEqual(self._count_runs(file_a), 1)
            self.assertEqual(self._count_runs(file_b), 0)

            handler.close()

    def _count_runs(self, filename):
        # The file was written by this test, so it is not untrusted input.
        return len(ElementTree.parse(filename).getroot().findall("run"))  # noqa: S314

    def _finish_run(self, run):
        run.status = "true"
        run.category = "correct"
        run.values = {"cputime": 1.0, "walltime": 1.0}
