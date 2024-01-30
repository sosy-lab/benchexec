# SPDX-FileCopyrightText: 2020-2021 CASTOR Software Research Centre
# <https://www.castor.kth.se/>
# SPDX-FileCopyrightText: 2020-2021 Johan Paulsson

# SPDX-License-Identifier: Apache-2.0

from benchexec.model import Run
from benchexec import result
import json
import os
import logging


class P4SetupHandler(object):
    """
    This class creates a new set of runs in the given benchmark.
    It will create on run for each test in the test_dict. If no
    property file or expected file is given, default will be used.
    """

    def __init__(self, benchmark, test_dict):
        self.benchmark = benchmark
        self.test_dict = test_dict

    def update_runsets(self):
        for runSet in self.benchmark.run_sets:
            # Divide the defined run into multiple run if necessery. Check len of runs: If 0, the setup went wrong.
            if len(runSet.runs) > 0:
                old_run = runSet.runs[0]
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
                for module_name in self.test_dict:
                    for test_name in self.test_dict[module_name]:
                        run = Run(f"{module_name}.{test_name}", "", "", "", runSet)
                        prop = [result.Property("/", False, "Yo")]
                        run.properties = prop
                        if run.identifier in expected_dict and len(prop) > 0:
                            run.expected_results[prop[0].filename] = (
                                result.ExpectedResult(
                                    expected_dict[run.identifier] == "True"
                                    or expected_dict[run.identifier] == "true",
                                    None,
                                )
                            )
                        else:
                            run.expected_results[prop[0].filename] = (
                                result.ExpectedResult(True, None)
                            )
                        runSet.runs.append(run)

    def _read_expected_result_json(self, json_file_path):
        with open(json_file_path) as json_file:
            data = json.load(json_file)

            return data
