# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

"""
    Unit tests for pqos module
"""
import json
import copy
import unittest
from subprocess import CalledProcessError
from unittest.mock import patch, MagicMock
from benchexec.pqos import Pqos

mock_pqos_wrapper_output = {
    "load_pqos": {
        "function_output": {},
        "returncode": 0,
        "function": "pqos_init",
        "error": False,
        "message": "MSR interface intialised",
    },
    "check_capability": {
        "function_output": {"mem_size": 32, "cdp_on": 0, "num_classes": 4},
        "returncode": 0,
        "function": "get_capability_info",
        "error": False,
        "message": "Retrieved l3ca capability",
    },
    "allocate_resource": {
        "function_output": {"cache_per_run": 4, "cores": {0: 0, 1: 0}},
        "returncode": 0,
        "function": "allocate_resource",
        "error": False,
        "message": "Allocated l3ca",
    },
    "monitor_events": {
        "function_output": {
            "monitoring_data": [
                {
                    "cores": [0, 1, 2],
                    "ipc": 0.987,
                    "llc_misses": 10240,
                    "llc": {"avg": 25028, "max": 30000},
                    "mbm_local": {"avg": 25028, "max": 30000},
                }
            ]
        },
        "returncode": 0,
        "function": "monitor_events",
        "error": False,
        "message": "Event monitoring successfull",
    },
    "reset_monitoring": {
        "returncode": 0,
        "function": "reset_monitoring",
        "error": False,
        "message": "Reset monitoring successfull",
    },
    "reset_resources": {
        "returncode": 0,
        "function": "reset_resources",
        "error": False,
        "message": "Resource reset successfull",
    },
}

mock_pqos_wrapper_error = {
    "function": "mock_function",
    "message": "error in pqos_wrapper function",
    "returncode": 1,
    "error": True,
    "function_output": {},
}


def mock_check_output(args_list, **kwargs):
    """
    mock for subprocess.check_output function, this function returns a dummy
    pqos_wrapper CLI output.
    """
    return json.dumps(mock_pqos_wrapper_output)


def mock_check_output_error(args_list, **kwargs):
    """
    mock for subprocess.check_output, returns a dummy error output of pqos_wrapper
    """
    raise CalledProcessError(1, "cmd", json.dumps(mock_pqos_wrapper_error))


def mock_check_output_capability_error(args_list, **kwargs):
    """
    mock for subprocess.check_output, returns a success pqos_wrapper output
    if get_capability function is called otherwise returns a dummy error output
    """
    if "-c" in args_list:
        return mock_check_output(args_list, **kwargs)
    mock_check_output_error(args_list, **kwargs)  # noqa: R503 always raises


class MockPopen:
    """
    A Mock class for subprocess.Popen
    """

    def __init__(self, args_list, universal_newlines=None, **kwargs):
        assert universal_newlines  # required for this mock
        self.args_list = args_list
        self.returncode = 0

    def send_signal(self, signal):
        """
        mock Popen.send_signal function
        """
        return 0

    def kill(self):
        """
        mock Popen.kill function
        """
        return 0

    def communicate(self):
        """
        mock Popen.communicate function
        """
        if self.returncode == 0:
            return (mock_check_output(self.args_list), None)
        return (None, json.dumps(mock_pqos_wrapper_error))


def mock_popen(args_list, **kwargs):
    """
    A mock function to create a MockPopen object with given arguments
    """
    return MockPopen(args_list, **kwargs)


class TestPqos(unittest.TestCase):
    """
    Unit tests for pqos module
    """

    @patch("benchexec.pqos.find_executable2", return_value="/path/to/pqos_wrapper/lib")
    def test_pqos_init(self, mock_find_executable):
        """
        Test for initialisation of pqos module
        """
        pqos = Pqos()
        self.assertIsInstance(pqos, Pqos)
        self.assertIsNotNone(pqos.executable_path, True)

    @patch("benchexec.pqos.find_executable2", return_value=None)
    def test_pqos_init_error(self, mock_find_executable):
        """
        Test for initialisation of pqos module when pqos_wrapper CLI is not present
        in the system.
        """
        pqos = Pqos()
        self.assertIsInstance(pqos, Pqos)
        self.assertIsNone(pqos.executable_path, False)

    @patch("benchexec.pqos.find_executable2", return_value="/path/to/pqos_wrapper/lib")
    @patch("benchexec.pqos.check_output", side_effect=mock_check_output)
    @patch("benchexec.pqos.Popen", side_effect=mock_popen)
    def test_pqos_execute_command(
        self, mock_find_executable, mock_check_output, mock_popen
    ):
        """
        Test for Pqos.execute_command function
        """
        pqos = Pqos()
        ret = pqos.execute_command("mon", "reset_monitoring", True, "-rm")
        self.assertEqual(ret, True)
        ret = pqos.execute_command("l3ca", "check_capability", False, "-c", "l3ca")
        self.assertEqual(ret, True)
        ret = pqos.execute_command(
            "l3ca", "allocate_resource", False, "-a", "l3ca", "[[0,1],[2,3]]"
        )
        self.assertEqual(ret, True)
        ret = pqos.execute_command("l3ca", "reset_resources", True, "-r")
        self.assertEqual(ret, True)
        ret = pqos.execute_command(
            "mon", "monitor_events", False, "-m", "[[0,1],[2,3]]"
        )
        self.assertEqual(ret, True)

    @patch("benchexec.pqos.find_executable2", return_value=None)
    def test_pqos_execute_command_cli_non_existent(self, mock_find_executable):
        """
        Test for Pqos.execute_command function when pqos_wrapper CLI is not present.
        """
        pqos = Pqos()
        ret = pqos.execute_command("mon", "reset_monitoring", True, "-rm")
        self.assertEqual(ret, False)
        ret = pqos.execute_command("l3ca", "check_capability", False, "-c", "l3ca")
        self.assertEqual(ret, False)
        ret = pqos.execute_command(
            "l3ca", "allocate_resource", False, "-a", "l3ca", "[[0,1],[2,3]]"
        )
        self.assertEqual(ret, False)
        ret = pqos.execute_command("l3ca", "reset_resources", True, "-r")
        self.assertEqual(ret, False)
        ret = pqos.execute_command(
            "mon", "monitor_events", False, "-m", "[[0,1],[2,3]]"
        )
        self.assertEqual(ret, False)

    @patch("benchexec.pqos.find_executable2", return_value="/path/to/pqos_wrapper/lib")
    @patch("benchexec.pqos.check_output", side_effect=mock_check_output_error)
    def test_pqos_execute_command_cli_error(
        self, mock_find_executable, mock_check_output
    ):
        """
        Test for Pqos.execute_command function when pqos_wrapper throws an error
        """
        pqos = Pqos()
        ret = pqos.execute_command("mon", "reset_monitoring", True, "-rm")
        self.assertEqual(ret, False)
        ret = pqos.execute_command("l3ca", "check_capability", False, "-c", "l3ca")
        self.assertEqual(ret, False)
        ret = pqos.execute_command(
            "l3ca", "allocate_resource", False, "-a", "l3ca", "[[0,1],[2,3]]"
        )
        self.assertEqual(ret, False)
        ret = pqos.execute_command("l3ca", "reset_resources", True, "-r")
        self.assertEqual(ret, False)

    @patch("benchexec.pqos.find_executable2", return_value="/path/to/pqos_wrapper/lib")
    @patch("benchexec.pqos.check_output", side_effect=mock_check_output)
    def test_pqos_allocate_l3ca(self, mock_find_executable, mock_check_output):
        """
        Test for pqos.allocate_l3ca
        """
        pqos = Pqos()
        pqos.allocate_l3ca([[0, 1], [2, 3]])
        self.assertEqual(pqos.reset_required, True)

    @patch("benchexec.pqos.find_executable2", return_value="/path/to/pqos_wrapper/lib")
    @patch(
        "benchexec.pqos.check_output", side_effect=mock_check_output_capability_error
    )
    def test_pqos_allocate_l3ca_error(self, mock_find_executable, mock_check_output):
        """
        Test for pqos.allocate_l3ca when pqos_wrapper throws an error
        """
        pqos = Pqos()
        pqos.reset_resources = MagicMock(return_value=0)
        pqos.allocate_l3ca([[0, 1], [2, 3]])
        self.assertEqual(pqos.reset_required, False)
        pqos.reset_resources.assert_called_once_with()

    @patch("benchexec.pqos.find_executable2", return_value="/path/to/pqos_wrapper/lib")
    @patch("benchexec.pqos.check_output", side_effect=mock_check_output)
    @patch("benchexec.pqos.Popen", side_effect=mock_popen)
    def test_pqos_stop_monitoring(
        self, mock_find_executable, mock_check_output, mock_popen
    ):
        """
        Test for pqos.stop_monitoring
        """
        flatten_mon_data = {
            "ipc": 0.987,
            "llc_misses": 10240,
            "llc_avg": 25028,
            "llc_max": 30000,
            "mbm_local_avg": 25028,
            "mbm_local_max": 30000,
        }
        pqos = Pqos()
        pqos.start_monitoring([[0, 1, 2]])
        ret = pqos.stop_monitoring()
        self.assertDictEqual(ret, flatten_mon_data)
        self.assertEqual(pqos.mon_process, None)

    @patch("benchexec.pqos.find_executable2", return_value="/path/to/pqos_wrapper/lib")
    @patch("benchexec.pqos.Popen", side_effect=mock_popen)
    def test_pqos_stop_monitoring_not_started(self, mock_find_executable, mock_popen):
        """
        Test for pqos.stop_monitoring, when monitoring is not started before
        """
        pqos = Pqos()
        ret = pqos.stop_monitoring()
        self.assertDictEqual(ret, {})
        self.assertEqual(pqos.mon_process, None)

    @patch("benchexec.pqos.find_executable2", return_value="/path/to/pqos_wrapper/lib")
    @patch("benchexec.pqos.check_output", side_effect=mock_check_output)
    @patch("benchexec.pqos.Popen", side_effect=mock_popen)
    def test_pqos_stop_monitoring_error(
        self, mock_find_executable, mock_check_output, mock_popen
    ):
        """
        Test for pqos.stop_monitoring, when pqos_wrapper throws an error
        """
        pqos = Pqos()
        pqos.start_monitoring([[0, 1, 2]])
        pqos.mon_process.returncode = 1
        ret = pqos.stop_monitoring()
        self.assertDictEqual(ret, {})
        self.assertEqual(pqos.mon_process, None)

    def test_pqos_flatten_mon_data(self):
        """
        Test for Pqos.flatten_mon_data when single monitoring data is received
        """
        flatten_mon_data = {
            "ipc": 0.987,
            "llc_misses": 10240,
            "llc_avg": 25028,
            "llc_max": 30000,
            "mbm_local_avg": 25028,
            "mbm_local_max": 30000,
        }
        mon_data = copy.deepcopy(
            mock_pqos_wrapper_output["monitor_events"]["function_output"][
                "monitoring_data"
            ]
        )
        ret = Pqos.flatten_mon_data(mon_data)
        self.assertDictEqual(ret, flatten_mon_data)

    def test_pqos_flatten_mon_data_multiple(self):
        """
        Test for Pqos.flatten_mon_data when multiple monitoring data are received
        """
        flatten_mon_data_multiple = {
            "ipc_cpus0,1,2": 0.987,
            "llc_misses_cpus0,1,2": 10240,
            "llc_avg_cpus0,1,2": 25028,
            "llc_max_cpus0,1,2": 30000,
            "mbm_local_avg_cpus0,1,2": 25028,
            "mbm_local_max_cpus0,1,2": 30000,
            "ipc_cpus3,4,5": 0.987,
            "llc_misses_cpus3,4,5": 10240,
            "llc_avg_cpus3,4,5": 25028,
            "llc_max_cpus3,4,5": 30000,
            "mbm_local_avg_cpus3,4,5": 25028,
            "mbm_local_max_cpus3,4,5": 30000,
        }
        mon_data = copy.deepcopy(
            mock_pqos_wrapper_output["monitor_events"]["function_output"][
                "monitoring_data"
            ]
        )
        first_core_set = copy.deepcopy(mon_data[0])
        second_core_set = copy.deepcopy(mon_data[0])
        second_core_set["cores"] = [3, 4, 5]
        mon_data_multiple = [first_core_set, second_core_set]
        ret = Pqos.flatten_mon_data(mon_data_multiple)
        self.assertDictEqual(ret, flatten_mon_data_multiple)

    def test_pqos_convert_core_list(self):
        """
        Test for pqos.convert_core_list function
        """
        ret = Pqos.convert_core_list([[0, 1], [2, 3]])
        self.assertEqual(ret, "[[0,1],[2,3]]")
