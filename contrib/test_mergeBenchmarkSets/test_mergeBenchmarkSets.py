# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import copy
import sys
import unittest
import xml.etree.ElementTree as ET  # noqa: What's wrong with ET?

from contrib import mergeBenchmarkSets
from benchexec import result

sys.dont_write_bytecode = True  # prevent creation of .pyc files

mock_results = """<?xml version="1.0"?>
<!DOCTYPE result
  PUBLIC '+//IDN sosy-lab.org//DTD BenchExec result 1.18//EN'
  'https://www.sosy-lab.org/benchexec/result-1.18.dtd'>
<result benchmarkname="cpa-seq" date="2019-11-29 14:00:20 CET" endtime="2019-11-30T15:10:11.004407+01:00" generator="BenchExec 2.5" starttime="2019-11-29T14:01:23.164273+01:00" tool="CPAchecker" toolmodule="benchexec.tools.cpachecker" version="1.9">
  <columns>
    <column title="status"/>
    <column title="cputime"/>
    <column title="walltime"/>
  </columns>
  <systeminfo>
    <os name="Linux 4.15.0-70-generic"/>
    <cpu cores="8" frequency="3800000000Hz" model="Intel Xeon E3-1230 v5 @ 3.40 GHz"/>
    <ram size="33546305536B"/>
    <environment/>
  </systeminfo>
  <run name="../sv-benchmarks/c/array-examples/sanfoundry_24-1.yml" logfile="logfiles/sanfoundry_24-1.yml.log">
    <column title="cpuenergy" value="157.939331J"/>
    <column title="cputime" value="18.077505912s"/>
    <column title="host" value="apollon124"/>
    <column title="memory" value="624906240B"/>
    <column title="status" value="true"/>
    <column title="walltime" value="5.474685221910477s"/>
    <column hidden="true" title="blkio-read" value="0B"/>
    <column hidden="true" title="blkio-write" value="0B"/>
    <column hidden="true" title="category" value="correct"/>
    <column hidden="true" title="cpuCores" value="0,4,1,5,2,6,3,7"/>
    <column hidden="true" title="cpuenergy-pkg0" value="157.939331J"/>
    <column hidden="true" title="cpuenergy-pkg0-core" value="152.173279J"/>
    <column hidden="true" title="cpuenergy-pkg0-dram" value="16.833801J"/>
    <column hidden="true" title="memoryNodes" value="0"/>
    <column hidden="true" title="returnvalue" value="0"/>
  </run>
  <run name="../sv-benchmarks/c/reducercommutativity/rangesum05.yml" logfile="logfiles/rangesum05.yml.log">
    <column title="cpuenergy" value="5027.425903J"/>
    <column title="cputime" value="703.613562312s"/>
    <column title="host" value="apollon022"/>
    <column title="memory" value="2182410240B"/>
    <column title="status" value="false(unreach-call)"/>
    <column title="walltime" value="675.135140747996s"/>
    <column hidden="true" title="blkio-read" value="0B"/>
    <column hidden="true" title="blkio-write" value="0B"/>
    <column hidden="true" title="category" value="correct"/>
    <column hidden="true" title="cpuCores" value="0,4,1,5,2,6,3,7"/>
    <column hidden="true" title="cpuenergy-pkg0" value="5027.425903J"/>
    <column hidden="true" title="cpuenergy-pkg0-core" value="4366.581726J"/>
    <column hidden="true" title="cpuenergy-pkg0-dram" value="1893.130615J"/>
    <column hidden="true" title="memoryNodes" value="0"/>
    <column hidden="true" title="returnvalue" value="0"/>
  </run>
  <run name="../sv-benchmarks/c/array-examples/data_structures_set_multi_proc_trivial_ground.yml" logfile="logfiles/data_structures_set_multi_proc_trivial_ground.yml.log">
    <column title="cpuenergy" value="11577.313477J"/>
    <column title="cputime" value="962.726514515s"/>
    <column title="host" value="apollon085"/>
    <column title="memory" value="6377070592B"/>
    <column title="status" value="TIMEOUT"/>
    <column title="walltime" value="903.5037164168898s"/>
    <column hidden="true" title="blkio-read" value="0B"/>
    <column hidden="true" title="blkio-write" value="0B"/>
    <column hidden="true" title="category" value="error"/>
    <column hidden="true" title="cpuCores" value="0,4,1,5,2,6,3,7"/>
    <column hidden="true" title="cpuenergy-pkg0" value="11577.313477J"/>
    <column hidden="true" title="cpuenergy-pkg0-core" value="10705.700562J"/>
    <column hidden="true" title="cpuenergy-pkg0-dram" value="2652.688477J"/>
    <column hidden="true" title="exitsignal" value="9"/>
    <column hidden="true" title="memoryNodes" value="0"/>
    <column hidden="true" title="terminationreason" value="cputime"/>
  </run>
  <run name="../sv-benchmarks/c/array-fpi/indp4f.yml" logfile="logfiles/indp4f.yml.log">
    <column title="cpuenergy" value="58.927551J"/>
    <column title="cputime" value="6.646181369s"/>
    <column title="host" value="apollon024"/>
    <column title="memory" value="233844736B"/>
    <column title="status" value="false(unreach-call)"/>
    <column title="walltime" value="2.3128131250850856s"/>
    <column hidden="true" title="blkio-read" value="0B"/>
    <column hidden="true" title="blkio-write" value="0B"/>
    <column hidden="true" title="category" value="correct"/>
    <column hidden="true" title="cpuCores" value="0,4,1,5,2,6,3,7"/>
    <column hidden="true" title="cpuenergy-pkg0" value="58.927551J"/>
    <column hidden="true" title="cpuenergy-pkg0-core" value="56.604187J"/>
    <column hidden="true" title="cpuenergy-pkg0-dram" value="6.205261J"/>
    <column hidden="true" title="memoryNodes" value="0"/>
    <column hidden="true" title="returnvalue" value="0"/>
  </run>
  <run name="../sv-benchmarks/c/array-patterns/array28_pattern.yml" logfile="logfiles/array28_pattern.yml.log">
    <column title="cpuenergy" value="1270.774292J"/>
    <column title="cputime" value="146.010175303s"/>
    <column title="host" value="apollon068"/>
    <column title="memory" value="1779523584B"/>
    <column title="status" value="false(unreach-call)"/>
    <column title="walltime" value="56.699794229120016s"/>
    <column hidden="true" title="blkio-read" value="0B"/>
    <column hidden="true" title="blkio-write" value="0B"/>
    <column hidden="true" title="category" value="wrong"/>
    <column hidden="true" title="cpuCores" value="0,4,1,5,2,6,3,7"/>
    <column hidden="true" title="cpuenergy-pkg0" value="1270.774292J"/>
    <column hidden="true" title="cpuenergy-pkg0-core" value="1209.154663J"/>
    <column hidden="true" title="cpuenergy-pkg0-dram" value="207.455811J"/>
    <column hidden="true" title="memoryNodes" value="0"/>
    <column hidden="true" title="returnvalue" value="0"/>
  </run>
</result>
"""

mock_witness_1 = """<?xml version="1.0"?>
<!DOCTYPE result
  PUBLIC '+//IDN sosy-lab.org//DTD BenchExec result 1.18//EN'
  'https://www.sosy-lab.org/benchexec/result-1.18.dtd'>
<result benchmarkname="cpa-seq-validate-correctness-witnesses-cpa-seq" date="2019-11-30 16:07:04 CET" endtime="2019-11-30T17:44:11.345532+01:00" generator="BenchExec 2.5" starttime="2019-11-30T16:07:40.485316+01:00" tool="CPAchecker" toolmodule="benchexec.tools.cpachecker" version="1.9">
  <columns>
    <column title="status"/>
    <column title="cputime"/>
    <column title="walltime"/>
  </columns>
  <systeminfo>
    <os name="Linux 4.15.0-70-generic"/>
    <cpu cores="8" frequency="3800000000Hz" model="Intel Xeon E3-1230 v5 @ 3.40 GHz"/>
    <ram size="33546305536B"/>
    <environment/>
  </systeminfo>
  <run name="../sv-benchmarks/c/array-examples/sanfoundry_24-1.yml">
    <column title="cputime" value="919.135930672s"/>
    <column title="host" value="apollon103"/>
    <column title="memory" value="2308612096B"/>
    <column title="status" value="TIMEOUT (ERROR (1))"/>
    <column title="walltime" value="871.4290894800797s"/>
    <column hidden="true" title="blkio-read" value="0B"/>
    <column hidden="true" title="blkio-write" value="0B"/>
    <column hidden="true" title="category" value="error"/>
    <column hidden="true" title="cpuCores" value="0,4"/>
    <column hidden="true" title="memoryNodes" value="0"/>
    <column hidden="true" title="returnvalue" value="1"/>
  </run>
  <run name="../sv-benchmarks/c/array-examples/data_structures_set_multi_proc_trivial_ground.yml">
    <column title="cputime" value="0.96134539s"/>
    <column title="host" value="apollon098"/>
    <column title="memory" value="48615424B"/>
    <column title="status" value="ERROR (invalid witness file)"/>
    <column title="walltime" value="0.5851919981651008s"/>
    <column hidden="true" title="blkio-read" value="0B"/>
    <column hidden="true" title="blkio-write" value="0B"/>
    <column hidden="true" title="category" value="error"/>
    <column hidden="true" title="cpuCores" value="2,6"/>
    <column hidden="true" title="memoryNodes" value="0"/>
    <column hidden="true" title="returnvalue" value="1"/>
  </run>
  <run name="../sv-benchmarks/c/array-patterns/array28_pattern.yml">
    <column title="cputime" value="7.220555471s"/>
    <column title="host" value="apollon093"/>
    <column title="memory" value="223555584B"/>
    <column title="status" value="true"/>
    <column title="walltime" value="3.8292284929193556s"/>
    <column hidden="true" title="blkio-read" value="0B"/>
    <column hidden="true" title="blkio-write" value="0B"/>
    <column hidden="true" title="category" value="correct"/>
    <column hidden="true" title="cpuCores" value="1,5"/>
    <column hidden="true" title="memoryNodes" value="0"/>
    <column hidden="true" title="returnvalue" value="0"/>
  </run>
</result>
"""

mock_witness_2 = """<?xml version="1.0"?>
<!DOCTYPE result
  PUBLIC '+//IDN sosy-lab.org//DTD BenchExec result 1.18//EN'
  'https://www.sosy-lab.org/benchexec/result-1.18.dtd'>
<result benchmarkname="cpa-seq-validate-violation-witnesses-cpa-seq" date="2019-12-03 07:46:25 CET" endtime="2019-12-03T08:32:39.564187+01:00" generator="BenchExec 2.5" starttime="2019-12-03T07:51:26.047090+01:00" tool="CPAchecker" toolmodule="benchexec.tools.cpachecker" version="1.9">
  <columns>
    <column title="status"/>
    <column title="cputime"/>
    <column title="walltime"/>
  </columns>
  <systeminfo>
    <os name="Linux 4.15.0-70-generic"/>
    <cpu cores="8" frequency="3800000000Hz" model="Intel Xeon E3-1230 v5 @ 3.40 GHz"/>
    <ram size="33546305536B"/>
    <environment/>
  </systeminfo>
  <run name="../sv-benchmarks/c/reducercommutativity/rangesum05.yml">
    <column title="cputime" value="10.069947319s"/>
    <column title="host" value="apollon019"/>
    <column title="memory" value="298663936B"/>
    <column title="status" value="false(unreach-call)"/>
    <column title="walltime" value="5.824956073000067s"/>
    <column hidden="true" title="blkio-read" value="0B"/>
    <column hidden="true" title="blkio-write" value="0B"/>
    <column hidden="true" title="category" value="correct"/>
    <column hidden="true" title="cpuCores" value="2,6"/>
    <column hidden="true" title="memoryNodes" value="0"/>
    <column hidden="true" title="returnvalue" value="0"/>
    <column hidden="true" title="starttime" value="2019-12-03T08:09:52.416048+01:00"/>
  </run>
  <run name="../sv-benchmarks/c/array-fpi/indp4f.yml">
    <column title="cputime" value="6.499907904s"/>
    <column title="host" value="apollon026"/>
    <column title="memory" value="183717888B"/>
    <column title="status" value="ERROR (invalid witness syntax)"/>
    <column title="walltime" value="3.7764528109983075s"/>
    <column hidden="true" title="blkio-read" value="0B"/>
    <column hidden="true" title="blkio-write" value="0B"/>
    <column hidden="true" title="category" value="error"/>
    <column hidden="true" title="cpuCores" value="1,5"/>
    <column hidden="true" title="memoryNodes" value="0"/>
    <column hidden="true" title="returnvalue" value="0"/>
    <column hidden="true" title="starttime" value="2019-12-03T08:09:55.376890+01:00"/>
  </run>
</result>
"""

results_xml = ET.fromstring(mock_results)  # noqa S314, the XML is trusted
witness_xml_1 = ET.fromstring(mock_witness_1)  # noqa S314, the XML is trusted
witness_xml_2 = ET.fromstring(mock_witness_2)  # noqa S314, the XML is trusted

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
    return results_xml.find("run[@name='{}']".format(name))


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
        def assert_equal_ignore_space(fst, snd):
            fst = [x.strip() for x in fst if x.strip()]
            snd = [x.strip() for x in snd if x.strip()]
            self.assertEqual(fst, snd)

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
        self.assertTrue(element_trees_equal(results_xml, ET.fromstring(new_results)))
        self.assertTrue(
            element_trees_equal(witness_xml_1, ET.fromstring(new_witness_1))
        )
        self.assertTrue(
            element_trees_equal(witness_xml_2, ET.fromstring(new_witness_2))
        )
        # TODO: Still have to make sure that the doctype was actually added; probably not present in parsed ET
        assert_equal_ignore_space(mock_results, new_results)
        assert_equal_ignore_space(mock_witness_1, new_witness_1)
        assert_equal_ignore_space(mock_witness_2, new_witness_2)

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
