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

import collections
import logging
import subprocess
import signal
import re
from benchexec.util import find_executable
from decimal import Decimal

DOMAIN_PACKAGE = "package"
DOMAIN_CORE = "core"
DOMAIN_UNCORE = "uncore"
DOMAIN_DRAM = "dram"

class EnergyMeasurement(object):

    measurementProcess = None

    def start(self):
        """Starts the external measurement program. Raises a warning if it is already running."""
        assert not self.is_running(), 'Attempted to start an energy measurement while one was already running.'

        executable = find_executable('cpu-energy-meter', exitOnError=False)
        if executable is None: # not available on current system
            logging.debug('Energy measurement not available because cpu-energy-meter binary could not be found.')
            return

        self.measurementProcess = subprocess.Popen([executable], stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=10000)

    def stop(self):
        """Stops the external measurement program and adds its measurement result to the internal buffer."""
        consumed_energy = collections.defaultdict(dict)
        assert self.is_running(), 'Attempted to stop an energy measurement while none was running.'
        # cpu-energy-meter expects SIGINT to stop and report its result
        self.measurementProcess.send_signal(signal.SIGINT)
        (out, err) = self.measurementProcess.communicate()
        for line in out.splitlines():
            line = line.decode('ASCII')
            logging.debug("energy measurement output: %s", line)
            match = re.match('cpu(\d+)_([a-z]+)_joules=(\d+\.?\d*)', line)
            if not match:
                continue

            cpu, domain, energy = match.groups()
            cpu = int(cpu)
            energy = Decimal(energy)

            consumed_energy[cpu][domain] = energy
        return consumed_energy


    def is_running(self):
        """Returns True if there is currently an instance of the external measurement program running, False otherwise."""
        return (self.measurementProcess is not None and self.measurementProcess.poll() is None)
