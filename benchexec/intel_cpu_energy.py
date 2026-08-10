# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import threading
import collections
import logging
from pathlib import Path
from dataclasses import dataclass
from decimal import Decimal
import sys
import subprocess
from time import sleep

rapl_path = Path("/sys/class/powercap/intel-rapl/")


@dataclass
class EnergyWrapper:  # This wrapper is needed to keep immutability in the Domain and Package classes while still allowing energy values to be updated
    last_value: int
    total: int = 0


class AreaOfMeasurement:
    def update_value(self):
        """update the energy values of current domain or package, this checks for overflows as well"""
        new_energy = int(get_path_content(self.path / "energy_uj"))
        if self.energy.total == 0 and self.energy.last_value == 0:  # first measurement
            self.energy.last_value = new_energy

        elif new_energy <= self.energy.last_value:  # overflow
            overflow_border = int(get_path_content(self.path / "max_energy_range_uj"))
            self.energy.total += overflow_border - self.energy.last_value + new_energy
            self.energy.last_value = new_energy

        else:
            self.energy.total += new_energy - self.energy.last_value
            self.energy.last_value = new_energy


@dataclass(frozen=True)
class Domain(AreaOfMeasurement):
    name: str
    path: Path
    energy: EnergyWrapper


@dataclass(frozen=True)
class Package(AreaOfMeasurement):
    name: str
    path: Path
    energy: EnergyWrapper
    domains: list[Domain]

    def update_value(self):
        """This enables cleaner updating of values by eliminating the need for nested loops"""
        super().update_value()
        for domain in self.domains:
            domain.update_value()


class EnergyMeasurement(object):
    def __init__(self):
        self.update_thread = threading.Thread(target=self.update_values)
        self.stop_event = threading.Event()
        self.packages: list[Package] = []
        for package in sorted(
            p for p in rapl_path.glob("intel-rapl:*") if p.name.count(":") == 1
        ):
            p_name = get_path_content(package / "name")
            domains = []
            for domain in sorted(
                d for d in package.glob("intel-rapl:*") if d.name.count(":") == 2
            ):
                d_name = get_path_content(domain / "name")
                domains.append(Domain(d_name, domain, EnergyWrapper(0)))

            self.packages.append(Package(p_name, package, EnergyWrapper(0), domains))

    @classmethod
    def create_if_supported(cls):
        if not rapl_path.exists():
            logging.debug(
                'Intel RAPL Kernel module for energy measurement not available, try "modprobe intel-rapl-msr"'
            )
            return None
        return cls()

    def start(self):
        """Start the measurement"""
        self.stop_event.clear()
        self.update_thread.start()

    def stop(self):
        """Stop the measurement if it hasn't been stopped already
        This method has to return self because of the way the old cpu-energy-meter was implemented,
        changing this would require changing the readout in every other file"""
        if not self.update_thread.is_alive():
            return self
        self.stop_event.set()
        self.update_thread.join()
        return self

    def update_all(self):
        """this updates the counter for total energy consumed across all packages and domains"""
        for package in self.packages:
            package.update_value()

    def update_values(self):
        """this method is run by a thread to constantly sample energy values for overhead protection"""
        self.update_all()
        while not self.stop_event.wait(timeout=1.0):
            self.update_all
        self.update_all()

    def __str__(self):
        string = ""
        for package in self.packages:
            string += f"{package.name}: {package.energy.total} uj\n"
            for domain in package.domains:
                string += f"    {domain.name}: {domain.energy.total} uj\n"
        return string


def get_path_content(path):
    try:
        content = path.read_text().strip()
        return content
    except OSError as error:
        print(f"cannot read {path}: {error}")


def convert_to_joules(energy):
    """The values read from the energy_uj file are in microjoules and need to be converted to joules"""
    return Decimal(energy) / Decimal(1000000)


def format_energy_results(measurement):
    """Take the result of an energy measurement and return a flat dictionary that contains all values
    cpuenergy is calculated as total energy consumed by all packages
    package names are unique, we don't have to worry about collisions"""
    if not measurement:
        return {}
    result = {}
    total = Decimal(0)
    for package in measurement.packages:
        p_energy = convert_to_joules(package.energy.total)
        # psys describes energy usage of the entire system and is therefore not relevant for cpuenergy
        if not package.name == "psys":
            total += p_energy
            result[f"cpuenergy-{package.name}"] = p_energy
        else:
            result["psys"] = p_energy
        for domain in package.domains:
            d_energy = convert_to_joules(domain.energy.total)
            result[f"cpuenergy-{package.name}-{domain.name}"] = d_energy
    result["cpuenergy"] = total
    result = collections.OrderedDict(sorted(result.items()))
    return result


# for testing
if __name__ == "__main__":
    measurement = EnergyMeasurement.create_if_supported()
    print(measurement)
    print("starting measurement")
    measurement.start()
    print(measurement)
    if len(sys.argv) < 2:
        sleep(3)
    else:
        subprocess.run(sys.argv[1:])
    measurement.stop()
    print(measurement)
    print(format_energy_results(measurement))
