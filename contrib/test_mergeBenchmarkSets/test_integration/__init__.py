# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import filecmp
import os
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True  # prevent creation of .pyc files

here = os.path.relpath(os.path.dirname(__file__))
base_dir = os.path.join(here, "..", "..", "..")
merge_benchmark_sets = [
    sys.executable,
    os.path.join(base_dir, "contrib", "mergeBenchmarkSets.py"),
]

# Set to True to let tests overwrite the expected result with the actual result
# instead of letting them fail.
# Use this to update expected files if necessary. Do not commit this flag set to True!
OVERWRITE_MODE = False


class MergeBenchmarkSetsIntegrationTests(unittest.TestCase):
    def run_cmd(self, *args):
        try:
            output = subprocess.check_output(
                args=args, stderr=subprocess.STDOUT
            ).decode()
        except subprocess.CalledProcessError as e:
            print(e.output.decode())
            raise e
        print(output)
        return output

    def merge_tables_and_compare(
        self, resultfile, witness_files, no_overwrite=False, merge_suffix=""
    ):
        with tempfile.TemporaryDirectory() as tmp_dir:
            result = self.run_cmd(
                *merge_benchmark_sets
                + [resultfile]
                + witness_files
                + (["--no-overwrite-status-true"] if no_overwrite else [])
                + ["--outputpath", tmp_dir]
            ).strip()
            expected = os.path.join(
                here,
                "expected",
                os.path.basename(resultfile) + ".merged" + merge_suffix + ".xml.bz2",
            )
            if OVERWRITE_MODE:
                os.replace(result, expected)
            else:
                self.assert_content_equals(result, expected)

    def assert_content_equals(self, result, expected):
        self.assertTrue(
            filecmp.cmp(result, expected, shallow=False),
            "Contents of {0} do not match contents of {1}".format(result, expected),
        )

    def test_no_files(self):
        self.assertNotEqual(
            0,
            subprocess.call(
                merge_benchmark_sets, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            ),
            "expected error return code",
        )

    def test_only_resultfile(self):
        cmd = [
            *merge_benchmark_sets,
            os.path.join(here, "verified.xml.bz2"),
        ]
        self.assertNotEqual(
            0,
            subprocess.call(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE),
            "expected error return code",
        )

    def test_empty_resultfile(self):
        self.merge_tables_and_compare(
            os.path.join(here, "empty.xml.bz2"),
            [os.path.join(here, "validated.xml.bz2")],
        )

    def test_validated_correctness_witnesses(self):
        self.merge_tables_and_compare(
            os.path.join(
                here,
                "cpa-seq.2019-11-29_1400.results.sv-comp20_prop-reachsafety.ReachSafety-Arrays.xml.bz2",
            ),
            [
                os.path.join(
                    here,
                    "cpa-seq-validate-correctness-witnesses-cpa-seq.2019-11-30_1607.results.sv-comp20_prop-reachsafety.ReachSafety-Arrays.xml.bz2",
                )
            ],
            merge_suffix="-correctness-validation",
        )

    def test_validated_violation_witnesses(self):
        self.merge_tables_and_compare(
            os.path.join(
                here,
                "cpa-seq.2019-11-29_1400.results.sv-comp20_prop-reachsafety.ReachSafety-Arrays.xml.bz2",
            ),
            [
                os.path.join(
                    here,
                    "cpa-seq-validate-violation-witnesses-cpa-seq.2019-12-03_0746.results.sv-comp20_prop-reachsafety.ReachSafety-Arrays.xml.bz2",
                )
            ],
            merge_suffix="-violation-validation",
        )

    def test_two_witness_files(self):
        self.merge_tables_and_compare(
            os.path.join(
                here,
                "cpa-seq.2019-11-29_1400.results.sv-comp20_prop-reachsafety.ReachSafety-Arrays.xml.bz2",
            ),
            [
                os.path.join(
                    here,
                    "cpa-seq-validate-correctness-witnesses-cpa-seq.2019-11-30_1607.results.sv-comp20_prop-reachsafety.ReachSafety-Arrays.xml.bz2",
                ),
                os.path.join(
                    here,
                    "cpa-seq-validate-violation-witnesses-cpa-seq.2019-12-03_0746.results.sv-comp20_prop-reachsafety.ReachSafety-Arrays.xml.bz2",
                ),
            ],
        )

    def test_no_overwrite_status_true(self):
        self.merge_tables_and_compare(
            os.path.join(here, "verified.xml.bz2"),
            [os.path.join(here, "validated.xml.bz2")],
            no_overwrite=True,
            merge_suffix="-no-overwrite",
        )

    def test_no_overwrite_without_witness_file(self):
        self.merge_tables_and_compare(
            os.path.join(here, "verified.xml.bz2"),
            [],
            no_overwrite=True,
            merge_suffix="-no-validation",
        )
