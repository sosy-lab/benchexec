# BenchExec is a framework for reliable benchmarking.
# This file is part of BenchExec.
#
# Copyright (C) 2007-2015  Dirk Beyer
# All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
    This module contains the Pqos class which is used to interact with pqos_wrapper cli
    to allocate equal cache for each thread and isolate cache of two individual threads.
"""

import os
import logging
import json
from subprocess import check_output, CalledProcessError, STDOUT
from benchexec.util import find_executable, get_capability, check_msr


class Pqos(object):
    """
        The Pqos class defines methods to interact with pqos_wrapper cli.
    """

    CMD = "pqos_wrapper"
    CAP_SYS_RAWIO = "cap_sys_rawio"

    def __init__(self):
        self.reset_required = False
        self.cap = False
        self.cli_exists = False
        self.executable_path = find_executable(
            "pqos_wrapper", exitOnError=False, use_current_dir=False
        )
        if self.executable_path is not None:
            self.cli_exists = True
        else:
            logging.warning(
                "Could not set cache allocation, unable to find pqos_wrapper cli"
            )

    def execute_command(self, function, suppress_warning, *args):
        """
            Execute a given pqos_wrapper command and log the output
        """
        if self.cli_exists:
            args_list = [self.CMD] + list(args)
            try:
                ret = json.loads(check_output(args_list, stderr=STDOUT))
                logging.debug(ret[function]["message"])
                return True
            except CalledProcessError as e:
                try:
                    ret = json.loads(e.output)
                    if not suppress_warning:
                        logging.warning(
                            "Could not set cache allocation...{}".format(ret["message"])
                        )
                        self.check_for_errors()
                except ValueError:
                    if not suppress_warning:
                        logging.warning(
                            "Could not set cache allocation...Unable to execute command {}".format(
                                " ".join(args_list)
                            )
                        )
        return False

    def check_capacity(self, technology):
        """
            Check if given intel rdt is supported.
        """
        if self.execute_command("check_capability", False, "-c", technology):
            self.cap = True

    def convert_core_list(self, core_assignment):
        """
            Convert a double list to a string.
        """
        ret = []
        for benchmark in core_assignment:
            ret.append("[" + ",".join(str(core) for core in benchmark) + "]")
        return "[" + ",".join(ret) + "]"

    def allocate_l3ca(self, core_assignment):
        """
            This method checks if L3CAT is available and calls pqos_wrapper to
            allocate equal cache to each thread.
        """
        self.check_capacity("l3ca")
        if self.cap:
            core_string = self.convert_core_list(core_assignment)
            if self.execute_command(
                "allocate_resource", False, "-a", "l3ca", core_string
            ):
                self.reset_required = True
            else:
                self.reset_resources()

    def reset_resources(self):
        """
            This method resets all resources to default.
        """
        if self.reset_required:
            self.execute_command("reset_resources", True, "-r")
            self.reset_required = False

    def check_for_errors(self):
        """
            This method logs a detailed error on a failed pqos_error command.
        """
        cap = get_capability(self.executable_path)
        if cap["error"] == False:
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
            if msr["read"]:
                if not msr["write"]:
                    logging.warning(
                        "Add write permissions for msr module for {}".format(
                            msr["user"]
                        )
                    )
            else:
                logging.warning(
                    "Add read and write permissions for msr module for {}".format(
                        msr["user"]
                    )
                )
        else:
            logging.warning("Load msr module for using cache allocation")
