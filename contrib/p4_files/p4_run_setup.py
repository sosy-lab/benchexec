# SPDX-FileCopyrightText: 2020-2021 CASTOR Software Research Centre
# <https://www.castor.kth.se/>
# SPDX-FileCopyrightText: 2020-2021 Johan Paulsson

# SPDX-License-Identifier: Apache-2.0

from benchexec.model import Run, SourcefileSet
from benchexec import result
import json
import os
import logging
import sys


class P4SetupHandler(object):
    """
    This class creates a new set of runs in the given benchmark.
    It will create on run for each test in the test_dict. If no
    property file or expected file is given, default will be used.
    """

    def __init__(self, benchmark):
        self.benchmark = benchmark

    def update_runsets(self):
        for index, runSet in enumerate(self.benchmark.run_sets):
            runSet.log_folder += f"Runset_{runSet.index}/"
            if not os.path.exists(runSet.log_folder):
                os.mkdir(runSet.log_folder)
            # Divide the defined run into multiple run if necessery. Check len of runs: If 0, the setup went wrong.
            updated_runs = []
            for run in runSet.runs:
                old_run = run
                expected_result_filename = old_run.identifier
                if os.path.exists(expected_result_filename):
                    expected_dict = self._read_expected_result_json(
                        expected_result_filename
                    )
                else:
                    logging.info(
                        "Could not identify expected result file. Assuming all test is true."
                    )
                    expected_dict = {}
                prop = old_run.properties
                runSet.runs = []
                runSet.blocks = []

                # Check for most relevant option
                if len(runSet.options) != len(old_run.options):
                    run_specific_options = []
                    final_index = None
                    for i in range(len(runSet.options) - 1):
                        final_index = i
                        if not (
                            runSet.options[i] == old_run.options[i]
                            and runSet.options[i + 1] == old_run.options[i + 1]
                        ):
                            run_specific_options.append(old_run[i])
                            run_specific_options.append(old_run[i + 1])

                    run_specific_options.append(old_run.options[final_index:])

                # Blocks contains SourceFileSet for each run. Create one sourcefileset
                # for each module

                for module_name in old_run.test_dict:
                    for test_name in old_run.test_dict[module_name]:
                        run = Run(
                            f"{module_name}.{test_name}",
                            "",
                            "",
                            old_run.options,
                            runSet,
                        )
                        run.test_folder_name = old_run.test_folder_name
                        prop = [result.Property("/", False, "Yo")]
                        run.properties = prop
                        if run.identifier in expected_dict and len(prop) > 0:
                            run.expected_results[
                                prop[0].filename
                            ] = result.ExpectedResult(
                                expected_dict[run.identifier] == "True"
                                or expected_dict[run.identifier] == "true",
                                None,
                            )
                        else:
                            run.expected_results[
                                prop[0].filename
                            ] = result.ExpectedResult(True, None)

                        updated_runs.append(run)
            runSet.runs = updated_runs
            runSet.blocks.append(SourcefileSet("", index, updated_runs))

    def _read_expected_result_json(self, json_file_path):
        with open(json_file_path) as json_file:
            data = json.load(json_file)

            return data
