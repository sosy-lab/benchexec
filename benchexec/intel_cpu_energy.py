# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import collections
import logging
import os
import subprocess
import signal
import re
from benchexec.util import find_executable2
from decimal import Decimal

DOMAIN_PACKAGE = "package"
DOMAIN_CORE = "core"
DOMAIN_UNCORE = "uncore"
DOMAIN_DRAM = "dram"


class EnergyMeasurement(object):
    def __init__(self, executable):
        self._executable = executable
        self._measurement_process = None

    @classmethod
    def create_if_supported(cls):
        executable = find_executable2("cpu-energy-meter")
        if executable is None:  # not available on current system
            logging.debug(
                "Energy measurement not available because cpu-energy-meter binary could not be found."
            )
            return None

        return cls(executable)

    def start(self):
        """Starts the external measurement program."""
        assert (
            not self.is_running()
        ), "Attempted to start an energy measurement while one was already running."

        self._measurement_process = subprocess.Popen(
            [self._executable, "-r"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            bufsize=10_000,
            preexec_fn=os.setpgrp,  # Prevent delivery of Ctrl+C to subprocess
        )

    def stop(self):
        """Stops the external measurement program and returns the measurement result,
        if the measurement was running."""
        consumed_energy = collections.defaultdict(dict)
        if not self.is_running():
            return None
        # cpu-energy-meter expects SIGINT to stop and report its result
        self._measurement_process.send_signal(signal.SIGINT)
        (out, err) = self._measurement_process.communicate()
        assert self._measurement_process.returncode is not None
        if self._measurement_process.returncode:
            logging.debug(
                "Energy measurement terminated with return code %s",
                self._measurement_process.returncode,
            )
        self._measurement_process = None
        for line in err.splitlines():
            logging.debug("energy measurement stderr: %s", line)
        for line in out.splitlines():
            logging.debug("energy measurement output: %s", line)
            match = re.match(r"cpu(\d+)_([a-z]+)_joules=(\d+\.?\d*)", line)
            if not match:
                continue

            cpu, domain, energy = match.groups()
            cpu = int(cpu)
            energy = Decimal(energy)

            consumed_energy[cpu][domain] = energy
        return consumed_energy

    def is_running(self):
        """Returns True if there is currently an instance of the external measurement program running, False otherwise."""
        return self._measurement_process is not None


def format_energy_results(energy):
    """Take the result of an energy measurement and return a flat dictionary that contains all values."""
    if not energy:
        return {}
    result = {}
    cpuenergy = Decimal(0)
    for pkg, domains in energy.items():
        for domain, value in domains.items():
            if domain == DOMAIN_PACKAGE:
                cpuenergy += value
            result[f"cpuenergy-pkg{pkg}-{domain}"] = value
    result["cpuenergy"] = cpuenergy
    result = collections.OrderedDict(sorted(result.items()))
    return result
