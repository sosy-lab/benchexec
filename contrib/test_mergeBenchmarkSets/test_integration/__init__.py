# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import filecmp
import io
import os
import sys
import tempfile
import unittest

from contextlib import redirect_stderr

from contrib import mergeBenchmarkSets

sys.dont_write_bytecode = True  # prevent creation of .pyc files

here = os.path.relpath(os.path.dirname(__file__))

# Set to True to let tests overwrite the expected result with the actual result
# instead of letting them fail.
# Use this to update expected files if necessary. Do not commit this flag set to True!
OVERWRITE_MODE = False


class MergeBenchmarkSetsIntegrationTests(unittest.TestCase):
    def merge_tables_and_compare(
        self, resultfile, witness_files, no_overwrite=False, merge_suffix=""
    ):
        with tempfile.TemporaryDirectory() as tmp_dir:
            mergeBenchmarkSets.main(
                [resultfile]
                + witness_files
                + (["--no-overwrite-status-true"] if no_overwrite else [])
                + ["--outputpath", tmp_dir]
            )
            result = os.path.join(
                tmp_dir, os.path.basename(resultfile) + ".merged.xml.bz2"
            )
            expected = os.path.join(
                here,
                "expected",
                f"{os.path.basename(resultfile)}.merged{merge_suffix}.xml.bz2",
            )
            if OVERWRITE_MODE:
                os.replace(result, expected)
            else:
                self.assert_content_equals(result, expected)

    def assert_content_equals(self, result, expected):
        self.assertTrue(
            filecmp.cmp(result, expected, shallow=False),
            f"Contents of {result} do not match contents of {expected}",
        )

    def test_no_files(self):
        with redirect_stderr(io.StringIO()):
            self.assertRaises(SystemExit, mergeBenchmarkSets.main, [])

    def test_only_resultfile(self):
        self.assertRaises(
            AssertionError,
            mergeBenchmarkSets.main,
            [os.path.join(here, "verified.xml.bz2")],
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
