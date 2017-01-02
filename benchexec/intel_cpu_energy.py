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

# prepare for Python 3
from __future__ import absolute_import, division, print_function, unicode_literals

# THIS MODULE HAS TO WORK WITH PYTHON 2.7!

import warnings
import subprocess
import signal
import re
from benchexec.util import find_executable


class EnergyMeasurement:

    cumulativeEnergy = {} # cE[cpuNum][domainName]
    measurementProcess = None

    def start(self):
        """Starts the external measurement program. Raises a warning if it is already running."""
        if self.isRunning():
            warnings.warn('Attempted to start an energy measurement while one was already running.')
            return

        executable = find_executable('cpu-energy-meter', exitOnError=False)
        if executable is None: # not available on current system
            logging.debug('Energy measurement not available because cpu-energy-meter binary could not be found.')
            return

        self.measurementProcess = subprocess.Popen([executable], stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=10000)

        return self.cumulativeEnergy

    def stop(self):
        """Stops the external measurement program and adds its measurement result to the internal buffer. Raises a warning if the external program isn't running."""
        consumed_energy = {}
        if not self.isRunning():
            warnings.warn('Attempted to stop an energy measurement while none was running.')
        # cpu-energy-meter expects SIGINT to stop and report its result
        self.measurementProcess.send_signal(signal.SIGINT)
        (out, err) = self.measurementProcess.communicate()
        for line in out.splitlines():
            match = re.match('cpu(\d+)_([a-z]+)_joules=(\d+\.?\d*)', line.decode('UTF-8'))
            if not match:
                continue

            cpu, domain, energy = match.groups()
            cpu = int(cpu)
            energy = float(energy)

            if not cpu in self.cumulativeEnergy:
                self.cumulativeEnergy[cpu] = {}
            if not cpu in consumed_energy:
                consumed_energy[cpu] = {}

            if not domain in self.cumulativeEnergy[cpu]:
                self.cumulativeEnergy[cpu][domain] = 0
            consumed_energy[cpu][domain] = energy

            self.cumulativeEnergy[cpu][domain] += energy
        return consumed_energy


    def isRunning(self):
        """Returns True if there is currently an instance of the external measurement program running, False otherwise."""
        return (self.measurementProcess is not None and self.measurementProcess.poll() is None)

    def getEnergyPerCPU(self):
        """Returns the measured energy usage for each CPU and domain (as a list of dicts, where the list index corresponds to the CPU ID and the dict contains an entry for each supported energy domain)."""
        return self.cumulativeEnergy

    def getEnergySum(self):
        """Returns the measured energy usage for each domain, summed across all CPUs (as a dict of domains, where each entry represents the measured energy of that domain across all CPUs)."""
        energySum = {}
        for cpu in self.cumulativeEnergy:
            for domain in self.cumulativeEnergy[cpu]:
                if domain not in energySum:
                    energySum[domain] = 0
                energySum[domain] += self.cumulativeEnergy[cpu][domain]

        return energySum

    def clear(self):
        """Removes all measurements from the internal buffer."""
        cumulativeEnergy = {}

    def __add__(self, other):
        for cpu in cumulativeEnergy:
            for domain in cumulativeEnergy[cpu]:
                if domain not in energySum:
                    energySum[domain] = 0
                energySum[domain] += cumulativeEnergy[cpu][domain]
