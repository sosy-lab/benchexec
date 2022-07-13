# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import copy
import os.path
import sys
import unittest
import xml.etree.ElementTree as ET  # noqa: What's wrong with ET?

from contrib import mergeBenchmarkSets
from benchexec import result

sys.dont_write_bytecode = True  # prevent creation of .pyc files

results_xml = ET.parse(  # noqa S314, the XML is trusted
    os.path.join(os.path.dirname(__file__), "mock_results.xml")
).getroot()
witness_xml_1 = ET.parse(  # noqa S314, the XML is trusted
    os.path.join(os.path.dirname(__file__), "mock_witness_1.xml")
).getroot()
witness_xml_2 = ET.parse(  # noqa S314, the XML is trusted
    os.path.join(os.path.dirname(__file__), "mock_witness_2.xml")
).getroot()

files = [
    "../sv-benchmarks/c/array-examples/sanfoundry_24-1.yml",
    "../sv-benchmarks/c/array-examples/data_structures_set_multi_proc_trivial_ground.yml",
    "../sv-benchmarks/c/array-patterns/array28_pattern.yml",
    "../sv-benchmarks/c/reducercommutativity/rangesum05.yml",
    "../sv-benchmarks/c/array-fpi/indp4f.yml",
]


def mock_witness_sets():
    witness_sets = {}
    for witness in [witness_xml_1, witness_xml_2]:
        for run in witness.findall("run"):
            name = run.get("name")
            witness_sets[name] = run
    return [witness_sets]


def mock_get_verification_result(name):
    return results_xml.find(f"run[@name='{name}']")


def mock_get_witness(name):
    witness = mock_witness_sets()[0].get(name)
    if witness is None:
        raise NotImplementedError(name)
    return witness


def element_trees_equal(et1, et2):
    if len(et1) != len(et2) or et1.tag != et2.tag or et1.attrib != et2.attrib:
        return False
    return all(element_trees_equal(child1, child2) for child1, child2 in zip(et1, et2))


class TestMergeBenchmarkSets(unittest.TestCase):
    def test_only_elem(self):
        new_results = mergeBenchmarkSets.xml_to_string(results_xml)
        new_witness_1 = mergeBenchmarkSets.xml_to_string(witness_xml_1)
        new_witness_2 = mergeBenchmarkSets.xml_to_string(witness_xml_2)
        self.assertTrue(
            element_trees_equal(
                ET.fromstring(new_results), results_xml  # noqa S314, the XML is trusted
            )
        )
        self.assertTrue(
            element_trees_equal(
                ET.fromstring(new_witness_1),  # noqa S314, the XML is trusted
                witness_xml_1,
            )
        )
        self.assertTrue(
            element_trees_equal(
                ET.fromstring(new_witness_2),  # noqa S314, the XML is trusted
                witness_xml_2,
            )
        )

    def test_set_doctype(self):
        qualified_name = "result"
        public_id = "+//IDN sosy-lab.org//DTD BenchExec result 1.18//EN"
        system_id = "https://www.sosy-lab.org/benchexec/result-1.18.dtd"
        new_results = mergeBenchmarkSets.xml_to_string(
            results_xml, qualified_name, public_id, system_id
        )
        new_witness_1 = mergeBenchmarkSets.xml_to_string(
            witness_xml_1, qualified_name, public_id, system_id
        )
        new_witness_2 = mergeBenchmarkSets.xml_to_string(
            witness_xml_2, qualified_name, public_id, system_id
        )
        self.assertTrue(
            element_trees_equal(
                results_xml, ET.fromstring(new_results)  # noqa S314, the XML is trusted
            )
        )
        self.assertTrue(
            element_trees_equal(
                witness_xml_1,
                ET.fromstring(new_witness_1),  # noqa S314, the XML is trusted
            )
        )
        self.assertTrue(
            element_trees_equal(
                witness_xml_2,
                ET.fromstring(new_witness_2),  # noqa S314, the XML is trusted
            )
        )
        for xml in [new_results, new_witness_1, new_witness_2]:
            self.assertListEqual(
                [line.strip() for line in xml.splitlines()[1:4]],
                [
                    f"<!DOCTYPE {qualified_name}",
                    f"PUBLIC '{public_id}'",
                    f"'{system_id}'>",
                ],
            )

    def test_getWitnesses(self):
        witness1 = mergeBenchmarkSets.get_witnesses(witness_xml_1)
        witness2 = mergeBenchmarkSets.get_witnesses(witness_xml_2)
        self.assertEqual(3, len(witness1))
        self.assertEqual(2, len(witness2))
        self.assertSetEqual(
            {
                "../sv-benchmarks/c/array-examples/sanfoundry_24-1.yml",
                "../sv-benchmarks/c/array-examples/data_structures_set_multi_proc_trivial_ground.yml",
                "../sv-benchmarks/c/array-patterns/array28_pattern.yml",
            },
            set(witness1.keys()),
        )
        self.assertSetEqual(
            {
                "../sv-benchmarks/c/reducercommutativity/rangesum05.yml",
                "../sv-benchmarks/c/array-fpi/indp4f.yml",
            },
            set(witness2.keys()),
        )

    def test_getWitnessResult_no_witness(self):
        self.assertEqual(
            ("witness missing", result.CATEGORY_ERROR),
            mergeBenchmarkSets.get_witness_result(None, None),
        )
        self.assertEqual(
            ("witness missing", result.CATEGORY_ERROR),
            mergeBenchmarkSets.get_witness_result(None, results_xml.find("run")),
        )

    def test_getWitnessResult_no_verification_result(self):
        for file in files[:-1]:
            self.assertEqual(
                ("result invalid (not found)", result.CATEGORY_ERROR),
                mergeBenchmarkSets.get_witness_result(mock_get_witness(file), None),
            )
        self.assertEqual(
            ("witness invalid (not found)", result.CATEGORY_ERROR),
            mergeBenchmarkSets.get_witness_result(mock_get_witness(files[-1]), None),
        )

    def test_getWitnessResult(self):
        expected_results = [
            ("true", result.CATEGORY_CORRECT_UNCONFIRMED),
            ("result invalid (TIMEOUT)", result.CATEGORY_ERROR),
            ("result invalid (false(unreach-call))", result.CATEGORY_ERROR),
            ("false(unreach-call)", result.CATEGORY_CORRECT),
            ("witness invalid (false(unreach-call))", result.CATEGORY_ERROR),
        ]
        for expected, file in zip(expected_results, files):
            self.assertEqual(
                expected,
                mergeBenchmarkSets.get_witness_result(
                    mock_get_witness(file), mock_get_verification_result(file)
                ),
            )

    def test_getValidationResult_single_witness(self):
        expected_results = [
            ("true", result.CATEGORY_CORRECT_UNCONFIRMED),
            ("result invalid (TIMEOUT)", result.CATEGORY_ERROR),
            ("result invalid (false(unreach-call))", result.CATEGORY_ERROR),
            ("false(unreach-call)", result.CATEGORY_CORRECT),
            ("witness invalid (false(unreach-call))", result.CATEGORY_ERROR),
        ]
        for expected, file in zip(expected_results, files):
            run = mock_get_verification_result(file)
            status_from_verification = run.find('column[@title="status"]').get("value")
            category_from_verification = run.find('column[@title="category"]').get(
                "value"
            )
            actual = mergeBenchmarkSets.get_validation_result(
                run,
                mock_witness_sets(),
                status_from_verification,
                category_from_verification,
            )
            self.assertEqual(expected, actual[:2])
            self.assertEqual(
                (status_from_verification, category_from_verification), actual[2:]
            )

    def test_getValidationResult_multiple_witnesses(self):
        new_witness_results = [
            ("ERROR (invalid witness syntax)", result.CATEGORY_ERROR),
            ("ERROR (invalid witness file)", result.CATEGORY_ERROR),
            ("false (unreach-call)", result.CATEGORY_WRONG),
            ("true", result.CATEGORY_WRONG),
            ("false (unreach-call)", result.CATEGORY_CORRECT),
        ]
        expected_results = [
            ("witness invalid (true)", result.CATEGORY_ERROR),
            ("result invalid (TIMEOUT)", result.CATEGORY_ERROR),
            ("result invalid (false(unreach-call))", result.CATEGORY_ERROR),
            ("false(unreach-call)", result.CATEGORY_CORRECT),
            ("witness invalid (false(unreach-call))", result.CATEGORY_ERROR),
        ]
        witness_set_1 = mock_witness_sets()
        witness_set_2 = copy.deepcopy(witness_set_1)
        for expected, file, new_witness_result in zip(
            expected_results, files, new_witness_results
        ):
            verification_run = mock_get_verification_result(file)
            witness_run = witness_set_2[0].get(file)
            witness_run.find('column[@title="status"]').set(
                "value", new_witness_result[0]
            )
            witness_run.find('column[@title="category"]').set(
                "value", new_witness_result[1]
            )
            status_from_verification = verification_run.find(
                'column[@title="status"]'
            ).get("value")
            category_from_verification = verification_run.find(
                'column[@title="category"]'
            ).get("value")
            actual = mergeBenchmarkSets.get_validation_result(
                verification_run,
                witness_set_1 + [{file: witness_run}],
                status_from_verification,
                category_from_verification,
            )
            self.assertEqual(expected, actual[:2])
            self.assertEqual(
                (status_from_verification, category_from_verification), actual[2:]
            )

    def test_getValidationResult_coverage_error_call(self):
        expected_results = [
            (None, None),
            (None, None),
            ("false(unreach-call)", result.CATEGORY_CORRECT),
            (None, None),
            (None, None),
        ]
        for expected, file in zip(expected_results, files):
            run = copy.deepcopy(mock_get_verification_result(file))
            run.set("properties", "coverage-error-call")
            status_from_verification = run.find('column[@title="status"]').get("value")
            category_from_verification = run.find('column[@title="category"]').get(
                "value"
            )
            actual = mergeBenchmarkSets.get_validation_result(
                run,
                mock_witness_sets(),
                status_from_verification,
                category_from_verification,
            )
            self.assertEqual(expected, actual[:2])
            self.assertEqual(status_from_verification, actual[2])
            if file == "../sv-benchmarks/c/array-patterns/array28_pattern.yml":
                self.assertEqual(result.CATEGORY_CORRECT, actual[3])
                self.assertNotEqual(None, run.find('column[@title="score"]'))
            else:
                self.assertEqual(category_from_verification, actual[3])

    def test_getValidationResult_coverage_branches(self):
        for file in files:
            run = copy.deepcopy(mock_get_verification_result(file))
            run.set("properties", "coverage-branches")
            status_from_verification = run.find('column[@title="status"]').get("value")
            category_from_verification = run.find('column[@title="category"]').get(
                "value"
            )
            actual = mergeBenchmarkSets.get_validation_result(
                run,
                mock_witness_sets(),
                status_from_verification,
                category_from_verification,
            )
            self.assertTupleEqual(
                (
                    status_from_verification,
                    result.CATEGORY_CORRECT,
                    status_from_verification,
                    result.CATEGORY_CORRECT,
                ),
                actual,
            )
            self.assertNotEqual(None, run.find('column[@title="score"]'))

    def test_getValidationResult_malformed_coverage(self):
        modified_run = copy.deepcopy(
            results_xml.find(
                'run[@name="../sv-benchmarks/c/array-examples/sanfoundry_24-1.yml"]'
            )
        )
        modified_run.set("properties", "coverage-branches")
        modified_witness_run = copy.deepcopy(
            witness_xml_1.find(
                'run[@name="../sv-benchmarks/c/array-examples/sanfoundry_24-1.yml"]'
            )
        )
        coverage_column = ET.Element(
            "column",
            title="branches_covered",
            value="fifty percent",  # this cannot be parsed into a number
        )
        modified_witness_run.append(coverage_column)
        actual = mergeBenchmarkSets.get_validation_result(
            modified_run,
            [{modified_witness_run.get("name"): modified_witness_run}],
            result.RESULT_TRUE_PROP,
            result.CATEGORY_CORRECT,
        )
        # we should still be able to assign the correct results:
        self.assertTupleEqual(
            (
                result.RESULT_TRUE_PROP,
                result.CATEGORY_CORRECT,
                result.RESULT_TRUE_PROP,
                result.CATEGORY_CORRECT,
            ),
            actual,
        )
        # score should be None since we were not able to parse "fifty percent" above:
        self.assertTrue(modified_witness_run.find('column[@title="score"]') is None)

    def test_merge_no_witness(self):
        results_xml_cp1 = copy.deepcopy(results_xml)
        results_xml_cp2 = copy.deepcopy(results_xml)
        mergeBenchmarkSets.merge(results_xml_cp2, [], True)
        for run in results_xml_cp1.findall("run"):
            del run.attrib["logfile"]
        self.assertEqual(ET.tostring(results_xml_cp1), ET.tostring(results_xml_cp2))

    def test_merge(self):
        expected_results = [
            ("true", result.CATEGORY_CORRECT_UNCONFIRMED),
            ("false(unreach-call)", result.CATEGORY_CORRECT),
            ("TIMEOUT", result.CATEGORY_ERROR),
            ("witness invalid (false(unreach-call))", result.CATEGORY_ERROR),
            ("false(unreach-call)", result.CATEGORY_WRONG),
        ]
        results_xml_cp = copy.deepcopy(results_xml)
        mergeBenchmarkSets.merge(results_xml_cp, mock_witness_sets(), True)
        for expected, run in zip(expected_results, results_xml_cp.findall("run")):
            status = run.find('column[@title="status"]').get("value")
            category = run.find('column[@title="category"]').get("value")
            self.assertTupleEqual(expected, (status, category))

    def test_merge_no_overwrite(self):
        expected_results = [
            ("true", result.CATEGORY_CORRECT),
            ("false(unreach-call)", result.CATEGORY_CORRECT),
            ("TIMEOUT", result.CATEGORY_ERROR),
            ("witness invalid (false(unreach-call))", result.CATEGORY_ERROR),
            ("false(unreach-call)", result.CATEGORY_WRONG),
        ]
        results_xml_cp = copy.deepcopy(results_xml)
        mergeBenchmarkSets.merge(results_xml_cp, mock_witness_sets(), False)
        for expected, run in zip(expected_results, results_xml_cp.findall("run")):
            status = run.find('column[@title="status"]').get("value")
            category = run.find('column[@title="category"]').get("value")
            self.assertTupleEqual(expected, (status, category))

    def test_merge_no_status_no_category(self):
        expected_results = [("not found", result.CATEGORY_CORRECT)] * 5
        modified_results = copy.deepcopy(results_xml)
        for run in modified_results.findall("run"):
            status_column = run.find('column[@title="status"]')
            category_column = run.find('column[@title="category"]')
            run.remove(status_column)
            run.remove(category_column)
            run.set("properties", "coverage-branches")
        mergeBenchmarkSets.merge(modified_results, mock_witness_sets(), True)
        for expected, run in zip(expected_results, modified_results.findall("run")):
            status = run.find('column[@title="status"]').get("value")
            category = run.find('column[@title="category"]').get("value")
            self.assertTupleEqual(expected, (status, category))
