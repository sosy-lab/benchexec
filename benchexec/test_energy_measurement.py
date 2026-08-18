import os
import tempfile
import unittest
import collections
from unittest.mock import patch
from pathlib import Path
from time import sleep

from benchexec import intel_cpu_energy as energy


class TestEnergyMeasurement(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory(
            prefix="BenchExec_test_energy_measurement"
        )
        self.addCleanup(self.test_dir.cleanup)
            
        self.rapl_mock = Path(self.test_dir.name) / "intel-rapl"
        self.package_mock = self.rapl_mock / "intel-rapl:0"
        self.domain_mock = self.package_mock / "intel-rapl:0:0"
        self.domain_mock.mkdir(parents=True)

        (self.package_mock / "name").write_text("package")
        (self.package_mock / "energy_uj").write_text("2000")
        (self.package_mock / "max_energy_range_uj").write_text("10000")
        (self.package_mock / "constraint_0_name").write_text("short_term")
        (self.package_mock / "constraint_0_power_limit_uw").write_text("1000")

        (self.domain_mock / "name").write_text("domain")
        (self.domain_mock / "energy_uj").write_text("200")
        (self.domain_mock / "max_energy_range_uj").write_text("10000")
        (self.domain_mock / "constraint_0_name").write_text("short_term")
        (self.domain_mock / "constraint_0_power_limit_uw").write_text("100")


    def test_run(self):
        with patch.object(energy, "rapl_path", self.rapl_mock):
            measurement = energy.EnergyMeasurement.create_if_supported()
            self.assertIsNotNone(measurement)
            self.assertEqual(measurement.interval, 10.0)
            self.assertEqual(measurement.packages[0].name, "package")
            self.assertEqual(measurement.packages[0].domains[0].name, "domain")
            measurement.start()
            sleep(0.1)  #we need a short sleep so that writing does not interfere with thread reading
            (self.package_mock / "energy_uj").write_text("4000")
            (self.domain_mock / "energy_uj").write_text("400")
            result = measurement.stop()
            self.assertIsNotNone(result)
            self.assertEqual(result.packages[0].energy.total, 2000)
            self.assertEqual(result.packages[0].domains[0].energy.total, 200)


    def test_get_path_content(self):
        with patch.object(energy, "rapl_path", self.rapl_mock):
            self.assertEqual(energy.get_path_content(self.package_mock / "name"), "package")
            self.assertRaises(OSError, energy.get_path_content, (self.rapl_mock / "does_not_exist"))
            self.assertEqual(energy.get_path_content(self.package_mock / "energy_uj"), "2000")
            os.chmod((self.package_mock / "name"), 0)
            self.assertRaises(OSError, energy.get_path_content, (self.package_mock / "name"))
        

    def test_format_results(self):
        with patch.object(energy, "rapl_path", self.rapl_mock):
            measurement = energy.EnergyMeasurement.create_if_supported()
            self.assertIsNotNone(measurement)
            measurement.start()
            sleep(0.1)  #we need a short sleep so that writing does not interfere with thread reading
            (self.package_mock / "energy_uj").write_text("4000")
            (self.domain_mock / "energy_uj").write_text("400")
            result = measurement.stop()
            self.assertIsNotNone(result)

            expectedResult = {}
            expectedResult["cpuenergy"] = energy.convert_to_joules(2000)
            expectedResult["cpuenergy-package"] = energy.convert_to_joules(2000)
            expectedResult["cpuenergy-package-domain"] = energy.convert_to_joules(200)
            expectedResult = collections.OrderedDict(sorted(expectedResult.items()))

            self.assertEqual(expectedResult, energy.format_energy_results(result))

    def test_error(self):
        """this test is expected to print an error message, it's not actually an error"""
        with patch.object(energy, "rapl_path", self.rapl_mock):
            measurement = energy.EnergyMeasurement.create_if_supported()
            measurement.start()
            os.chmod((self.package_mock / "energy_uj"), 0)
            result = measurement.stop()
            self.assertIsNone(result)
            self.assertIsNone(measurement.packages)

            os.chmod((self.package_mock / "energy_uj"), 0o666)
            (self.package_mock / "energy_uj").write_text("some_text")
            measurement.start()
            result = measurement.stop()
            self.assertIsNone(result)
            self.assertIsNone(measurement.packages)


