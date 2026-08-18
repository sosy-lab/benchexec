import os
import tempfile
import unittest
from pathlib import Path
from time import sleep

from benchexec import intel_cpu_energy as energy


class TestEnergyMeasurement(unittest.TestCase):
    def test_run(self):
        measurement = energy.EnergyMeasurement.create_if_supported()
        if measurement is None:
            self.skipTest("Energy Measurements not available")
        measurement.start()
        sleep(1)
        measurement.stop()

    def test_get_path_content(self):
        test_dir = tempfile.TemporaryDirectory(
            prefix="BenchExec_test_energy_measurement"
        )
        self.assertEqual(
            energy.get_path_content(Path(test_dir.name + "does_not_exist")), "0"
        )
        with tempfile.NamedTemporaryFile(dir=test_dir.name) as test_file:
            self.assertEqual(energy.get_path_content(Path(test_file.name)), "")
            test_file.write(b"test\n")
            test_file.seek(0)
            self.assertEqual(energy.get_path_content(Path(test_file.name)), "test")
            os.chmod(test_file.name, 0)
            self.assertEqual(energy.get_path_content(Path(test_file.name)), "0")
        test_dir.cleanup()

    def test_format_results(self):
        measurement = energy.EnergyMeasurement.create_if_supported()
        if measurement is None:
            self.skipTest("Energy Measurements not available")
        result = energy.format_energy_results(measurement)
        for r in result:
            self.assertEqual(result[r], 0)

    def test_error_event(self):
        """this test is expected to print an error message, it's not actually an error"""
        measurement = energy.EnergyMeasurement.create_if_supported()
        if measurement is None:
            self.skipTest("Energy Measurements not available")
        measurement.start()
        sleep(0.5)
        energy.EnergyMeasurement.error_event.set()
        sleep(0.5)
        result = measurement.stop()
        self.assertEqual(result, None)
