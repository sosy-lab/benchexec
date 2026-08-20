# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import collections
import os
import tempfile
import unittest
from pathlib import Path
from time import sleep
from unittest.mock import patch

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
            sleep(
                0.1
            )  # we need a short sleep so that writing does not interfere with thread reading
            (self.package_mock / "energy_uj").write_text("4000")
            (self.domain_mock / "energy_uj").write_text("400")
            result = measurement.stop()
            self.assertIsNotNone(result)
            self.assertEqual(result.packages[0].energy.total, 2000)
            self.assertEqual(result.packages[0].domains[0].energy.total, 200)

    def test_get_path_content(self):
        with patch.object(energy, "rapl_path", self.rapl_mock):
            self.assertEqual(
                energy.get_path_content(self.package_mock / "name"), "package"
            )
            self.assertRaises(
                OSError, energy.get_path_content, (self.rapl_mock / "does_not_exist")
            )
            self.assertEqual(
                energy.get_path_content(self.package_mock / "energy_uj"), "2000"
            )
            os.chmod((self.package_mock / "name"), 0)
            self.assertRaises(
                OSError, energy.get_path_content, (self.package_mock / "name")
            )

    def test_format_results(self):
        with patch.object(energy, "rapl_path", self.rapl_mock):
            measurement = energy.EnergyMeasurement.create_if_supported()
            self.assertIsNotNone(measurement)
            measurement.start()
            sleep(
                0.1
            )  # we need a short sleep so that writing does not interfere with thread reading
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

            os.chmod((self.package_mock / "energy_uj"), 0o660)
            (self.package_mock / "energy_uj").write_text("some_text")
            measurement.start()
            result = measurement.stop()
            self.assertIsNone(result)
            self.assertIsNone(measurement.packages)

    def test_dual_cpu(self):
        with patch.object(energy, "rapl_path", self.rapl_mock):
            second_package_mock = self.rapl_mock / "intel-rapl:1"
            second_domain_mock = second_package_mock / "intel-rapl:1:0"
            second_domain_mock.mkdir(parents=True)

            (second_package_mock / "name").write_text("package2")
            (second_package_mock / "energy_uj").write_text("1000")
            (second_package_mock / "max_energy_range_uj").write_text("10000")
            (second_package_mock / "constraint_0_name").write_text("short_term")
            (second_package_mock / "constraint_0_power_limit_uw").write_text("1000")

            (second_domain_mock / "name").write_text("domain2")
            (second_domain_mock / "energy_uj").write_text("100")
            (second_domain_mock / "max_energy_range_uj").write_text("1000")
            (second_domain_mock / "constraint_0_name").write_text("short_term")
            (second_domain_mock / "constraint_0_power_limit_uw").write_text("100")

            measurement = energy.EnergyMeasurement.create_if_supported()
            if measurement is None:
                self.skipTest()
            self.assertEqual(len(measurement.packages), 2)
            self.assertEqual(measurement.packages[0].name, "package")
            self.assertEqual(measurement.packages[1].name, "package2")

            measurement.start()
            sleep(0.1)
            (second_package_mock / "energy_uj").write_text("4000")
            (second_domain_mock / "energy_uj").write_text("400")
            (self.package_mock / "energy_uj").write_text("4000")
            (self.domain_mock / "energy_uj").write_text("400")
            result = measurement.stop()
            result = energy.format_energy_results(result)
            if result is None:
                self.skipTest()
            self.assertEqual(
                result["cpuenergy-package"], energy.convert_to_joules(2000)
            )
            self.assertEqual(
                result["cpuenergy-package2"], energy.convert_to_joules(3000)
            )
            self.assertEqual(
                result["cpuenergy-package-domain"], energy.convert_to_joules(200)
            )
            self.assertEqual(
                result["cpuenergy-package2-domain2"], energy.convert_to_joules(300)
            )
            # total cpuenergy should be sum from all packages
            self.assertEqual(result["cpuenergy"], energy.convert_to_joules(5000))

    def test_psys(self):
        with patch.object(energy, "rapl_path", self.rapl_mock):
            psys_mock = self.rapl_mock / "intel-rapl:1"
            psys_mock.mkdir()

            (psys_mock / "name").write_text("psys")
            (psys_mock / "energy_uj").write_text("1000")
            (psys_mock / "max_energy_range_uj").write_text("10000")
            (psys_mock / "constraint_0_name").write_text("short_term")
            (psys_mock / "constraint_0_power_limit_uw").write_text("1000")

            measurement = energy.EnergyMeasurement.create_if_supported()
            if measurement is None:
                self.skipTest()
            self.assertEqual(len(measurement.packages), 2)
            self.assertEqual(measurement.packages[0].name, "package")
            self.assertEqual(measurement.packages[1].name, "psys")

            measurement.start()
            sleep(0.1)
            (psys_mock / "energy_uj").write_text("4000")
            (self.package_mock / "energy_uj").write_text("4000")
            (self.domain_mock / "energy_uj").write_text("400")
            result = measurement.stop()
            result = energy.format_energy_results(result)
            if result is None:
                self.skipTest()
            self.assertEqual(
                result["cpuenergy-package"], energy.convert_to_joules(2000)
            )
            self.assertEqual(result["systemenergy"], energy.convert_to_joules(3000))
            self.assertEqual(result["cpuenergy"], energy.convert_to_joules(2000))

    def test_overflow(self):
        with patch.object(energy, "rapl_path", self.rapl_mock):
            measurement = energy.EnergyMeasurement.create_if_supported()
            if measurement is None:
                self.skipTest()
            measurement.start()
            sleep(0.1)
            (self.package_mock / "energy_uj").write_text("1000")
            (self.domain_mock / "energy_uj").write_text("100")
            result = measurement.stop()
            self.assertIsNotNone(result)
            self.assertEqual(result.packages[0].energy.total, 9000)
            self.assertEqual(result.packages[0].domains[0].energy.total, 9900)
