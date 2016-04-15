import warnings
import subprocess
import signal
import re
from util import find_executable

class EnergyMeasurement:

    cumulativeEnergy = {} # cE[cpuNum][domainName]
    measurementProcess = None

    def start(self):
        """Starts the external measurement program. Raises a warning if it is already running."""
        if self.isRunning():
            warnings.warn('Attempted to start an energy measurement while one was already running.')
            return

        executable = find_executable('power_gadget', exitOnError=False)
        if executable is None: # not available on current system
            logging.debug('Energy measurement not available because read-energy.sh could not be found.')
            return

        self.measurementProcess = subprocess.Popen([executable], stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=10000)

    def stop(self):
        """Stops the external measurement program and adds its measurement result to the internal buffer. Raises a warning if the external program isn't running."""
        if not self.isRunning():
            warnings.warn('Attempted to stop an energy measurement while none was running.')
        # Our modified power_gadget version expects SIGINT to stop and report its result
        self.measurementProcess.send_signal(signal.SIGINT)

        (out, err) = self.measurementProcess.communicate()

        for line in out.splitlines():
            match = re.match('cpu(\d+)_([a-z]+)_Joules=(\d+\.?\d*)', line)
            if not match:
                continue

            cpu, domain, energy = match.groups()
            cpu = int(cpu)
            energy = float(energy)

            if not cpu in self.cumulativeEnergy:
                self.cumulativeEnergy[cpu] = {}

            if not domain in self.cumulativeEnergy[cpu]:
                self.cumulativeEnergy[cpu][domain] = 0

            self.cumulativeEnergy[cpu][domain] += energy

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
