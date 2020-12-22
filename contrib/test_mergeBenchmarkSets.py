# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import sys
import unittest
import xml.etree.ElementTree as ET

import mergeBenchmarkSets
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
  <run name="../sv-benchmarks/c/array-examples/sanfoundry_24-1.yml">
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
  <run name="../sv-benchmarks/c/reducercommutativity/rangesum05.yml">
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
  <run name="../sv-benchmarks/c/array-examples/data_structures_set_multi_proc_trivial_ground.yml">
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
  <run name="../sv-benchmarks/c/array-fpi/indp4f.yml">
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
  <run name="../sv-benchmarks/c/array-patterns/array28_pattern.yml">
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

results_xml = ET.fromstring(mock_results)
witness_xml_1 = ET.fromstring(mock_witness_1)
witness_xml_2 = ET.fromstring(mock_witness_2)

files = [
    "../sv-benchmarks/c/array-examples/sanfoundry_24-1.yml",
    "../sv-benchmarks/c/array-examples/data_structures_set_multi_proc_trivial_ground.yml",
    "../sv-benchmarks/c/array-patterns/array28_pattern.yml",
    "../sv-benchmarks/c/reducercommutativity/rangesum05.yml",
    "../sv-benchmarks/c/array-fpi/indp4f.yml",
]


class TestXMLToString(unittest.TestCase):
    def element_trees_equal(self, et1, et2):
        if len(et1) != len(et2) or et1.tag != et2.tag or et1.attrib != et2.attrib:
            return False
        return all(
            [
                self.element_trees_equal(child1, child2)
                for child1, child2 in zip(et1, et2)
            ]
        )

    def test_only_elem(self):

        new_results = mergeBenchmarkSets.xml_to_string(results_xml)
        new_witness_1 = mergeBenchmarkSets.xml_to_string(witness_xml_1)
        new_witness_2 = mergeBenchmarkSets.xml_to_string(witness_xml_2)
        self.assertTrue(
            self.element_trees_equal(ET.fromstring(new_results), results_xml)
        )
        self.assertTrue(
            self.element_trees_equal(ET.fromstring(new_witness_1), witness_xml_1)
        )
        self.assertTrue(
            self.element_trees_equal(ET.fromstring(new_witness_2), witness_xml_2)
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
        assert_equal_ignore_space(mock_results, new_results)
        assert_equal_ignore_space(mock_witness_1, new_witness_1)
        assert_equal_ignore_space(mock_witness_2, new_witness_2)


class TestWitnesses(unittest.TestCase):
    def mock_get_witness(self, name):
        if name in [
            "../sv-benchmarks/c/array-examples/sanfoundry_24-1.yml",
            "../sv-benchmarks/c/array-examples/data_structures_set_multi_proc_trivial_ground.yml",
            "../sv-benchmarks/c/array-patterns/array28_pattern.yml",
        ]:
            return witness_xml_1.find("run[@name='{}']".format(name))
        elif name in [
            "../sv-benchmarks/c/reducercommutativity/rangesum05.yml",
            "../sv-benchmarks/c/array-fpi/indp4f.yml",
        ]:
            return witness_xml_2.find("run[@name='{}']".format(name))
        raise NotImplementedError(name)

    def mock_get_verification_result(self, name):
        return results_xml.find("run[@name='{}']".format(name))

    def test_getWitnesses(self):
        witness1 = mergeBenchmarkSets.getWitnesses(witness_xml_1)
        witness2 = mergeBenchmarkSets.getWitnesses(witness_xml_2)
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
            mergeBenchmarkSets.getWitnessResult(None, None),
        )
        self.assertEqual(
            ("witness missing", result.CATEGORY_ERROR),
            mergeBenchmarkSets.getWitnessResult(None, results_xml.find("run")),
        )

    def test_getWitnessResult_no_verification_result(self):
        for file in files[:-1]:
            self.assertEqual(
                ("result invalid (not found)", result.CATEGORY_ERROR),
                mergeBenchmarkSets.getWitnessResult(self.mock_get_witness(file), None),
            )
        self.assertEqual(
            ("witness invalid (not found)", result.CATEGORY_ERROR),
            mergeBenchmarkSets.getWitnessResult(self.mock_get_witness(files[-1]), None),
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
                mergeBenchmarkSets.getWitnessResult(
                    self.mock_get_witness(file), self.mock_get_verification_result(file)
                ),
            )
