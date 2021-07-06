# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

"""
    This module contains the Pqos class which is used to interact with pqos_wrapper cli
    to allocate equal cache for each thread and isolate cache of two individual threads.
"""

import os
import logging
import json
import grp
from signal import SIGINT
from subprocess import check_output, CalledProcessError, STDOUT, Popen, PIPE
from benchexec.util import find_executable2, get_capability, check_msr


class Pqos(object):
    """
    The Pqos class defines methods to interact with pqos_wrapper cli.
    """

    CAP_SYS_RAWIO = "cap_sys_rawio"

    def __init__(self, show_warnings=False):
        self.reset_required = False
        self.show_warnings = show_warnings
        self.mon_process = None
        self.executable_path = find_executable2("pqos_wrapper")
        if self.executable_path is None:
            if self.show_warnings:
                logging.info(
                    "Unable to find pqos_wrapper, please install it for "
                    "cache allocation and monitoring if your CPU supports Intel RDT "
                    "(cf. https://gitlab.com/sosy-lab/software/pqos-wrapper)."
                )

    def execute_command(self, __type, function, suppress_warning, *args):
        """
        Execute a given pqos_wrapper command and log the output

            @__type: The type of command being executed (monitoring or l3ca)
            @function_name: The name of the function being executed in pqos_wrapper
            @suppress_warning: A boolean to decide wether to print warning on failing execution
        """
        if self.executable_path:
            args_list = [self.executable_path] + list(args)
            try:
                if "-m" in args_list:
                    self.mon_process = Popen(
                        args_list, stdout=PIPE, stderr=PIPE, universal_newlines=True
                    )
                else:
                    ret = json.loads(
                        check_output(args_list, stderr=STDOUT, universal_newlines=True)
                    )
                    logging.debug(ret[function]["message"])
                return True
            except CalledProcessError as e:
                if self.show_warnings and (not suppress_warning):
                    self.print_error_message(e.output, __type, args_list)
        return False

    def print_error_message(self, err, __type, args_list):
        """
        Prints error message returned from pqos_wrapper

            @err: The error output returned by pqos_wrapper
            @__type: The type of command being executed (monitoring or l3ca)
            @args_list: The command being executed as a list
        """
        msg_prefix = {
            "mon": "Could not monitor events",
            "l3ca": "Could not set cache allocation",
        }
        try:
            ret = json.loads(err)
            logging.warning("%s...%s", msg_prefix[__type], ret["message"])
            self.check_for_errors()
        except ValueError:
            logging.warning(
                "%s...Unable to execute command %s",
                msg_prefix[__type],
                " ".join(args_list),
            )

    def check_capacity(self, technology):
        """
        Check if given intel rdt is supported.

            @technology: The intel rdt to be tested
        """
        return self.execute_command(
            technology, "check_capability", False, "-c", technology
        )

    @staticmethod
    def convert_core_list(core_assignment):
        """
        Convert a double list to a string.

            @core_assignment: The double list of cores
        """
        ret = []
        for benchmark in core_assignment:
            ret.append("[" + ",".join(str(core) for core in benchmark) + "]")
        return "[" + ",".join(ret) + "]"

    def allocate_l3ca(self, core_assignment):
        """
        This method checks if L3CAT is available and calls pqos_wrapper to
        allocate equal cache to each thread.

            @core_assignment: The list of cores assigned to each run
        """
        if self.check_capacity("l3ca"):
            core_string = self.convert_core_list(core_assignment)
            if self.execute_command(
                "l3ca", "allocate_resource", False, "-a", "l3ca", core_string
            ):
                self.reset_required = True
            else:
                self.reset_resources()

    def start_monitoring(self, core_assignment):
        """
        This method checks if monitoring capability is available and calls pqos_wrapper to
        monitor events on given lists of cores.

            @core_assignment: The list of cores assigned to each run
        """
        if self.check_capacity("mon"):
            core_string = self.convert_core_list(core_assignment)
            self.execute_command("mon", "monitor_events", False, "-m", core_string)

    def stop_monitoring(self):
        """
        This method stops monitoring by sending SIGINT to the monitoring process
        and resets the RMID for monitored cores to 0
        """
        ret = {}
        if self.mon_process:
            self.mon_process.send_signal(SIGINT)
            mon_output = self.mon_process.communicate()
            if self.mon_process.returncode == 0:
                mon_data = json.loads(mon_output[0])
                logging.debug(mon_data["monitor_events"]["message"])
                ret = self.flatten_mon_data(
                    mon_data["monitor_events"]["function_output"]["monitoring_data"]
                )
            else:
                if self.show_warnings:
                    self.print_error_message(
                        mon_output[1], "mon", self.mon_process.args
                    )
            self.mon_process.kill()
            self.mon_process = None
        else:
            if self.show_warnings:
                logging.warning("No monitoring process started")
        return ret

    def reset_monitoring(self):
        """
        Reset monitoring RMID to 0 for all cores
        """
        self.execute_command("mon", "reset_monitoring", True, "-rm")

    @staticmethod
    def flatten_mon_data(mon_data):
        """
        Converts the monitoring data array received from pqos_wrapper
        to a flattened dictionary

            @mon_data: The array of data received from pqos_wrapper monitoring cli
        """
        flatten_dict = {}
        for data in mon_data:
            core_str = ",".join(str(core) for core in data["cores"])
            data.pop("cores", None)
            for key, val in data.items():
                if isinstance(val, dict):
                    for sub_key, sub_val in val.items():
                        if len(mon_data) > 1:
                            flatten_key = f"{key}_{sub_key}_cpus{core_str}"
                        else:
                            flatten_key = f"{key}_{sub_key}"
                        flatten_dict[flatten_key] = sub_val
                else:
                    if len(mon_data) > 1:
                        flatten_key = f"{key}_cpus{core_str}"
                    else:
                        flatten_key = key
                    flatten_dict[flatten_key] = val
        return flatten_dict

    def reset_resources(self):
        """
        This method resets all resources to default.
        """
        if self.reset_required:
            self.execute_command("l3ca", "reset_resources", True, "-r")
            self.reset_required = False

    def check_for_errors(self):
        """
        This method logs a detailed error on a failed pqos_error command.
        """
        cap = get_capability(self.executable_path)
        if cap["error"] is False:
            if self.CAP_SYS_RAWIO in cap["capabilities"]:
                if not all(x in cap["set"] for x in ["e", "p"]):
                    logging.warning(
                        "Insufficient capabilities for pqos_wrapper, Please add e,p in cap_sys_rawio capability set of pqos_wrapper"
                    )
            else:
                logging.warning(
                    "Insufficient capabilities for pqos_wrapper, Please set capabilitiy cap_sys_rawio with e,p for pqos_wrapper"
                )
        msr = check_msr()
        if msr["loaded"]:
            current_user = grp.getgrgid(os.getegid()).gr_name
            if msr["read"]:
                if not msr["write"]:
                    logging.warning(
                        "Add write permissions for msr module for %s", current_user
                    )
            else:
                logging.warning(
                    "Add read and write permissions for msr module for %s", current_user
                )
        else:
            logging.warning("Load msr module for using cache allocation/monitoring")
