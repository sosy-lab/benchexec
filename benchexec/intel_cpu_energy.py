# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import collections
import logging
import subprocess
import sys
import threading
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
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


class EnergyMeasurement:
    interval = 1000  # default measurement interval in seconds, derived from an assumed worst case of 250W energy consumption

    def __init__(self):
        self.stop_event = threading.Event()
        self.packages: list[Package] = []

        """We are searching for all available packages and domains
        Each one has a name file as well as the energy measurement related files
        example package name path: /sys/class/powercap/intel-rapl/intel-rapl:0/name
        example domain name path: /sys/class/powercap/intel-rapl/intel-rapl:0/intel-rapl:0:0/name"""
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
        self.calculate_interval()

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
        self.update_thread = threading.Thread(target=self.update_values)
        self.stop_event.clear()
        self.update_thread.start()

    def stop(self):
        """Stop the measurement if it hasn't been stopped already
        This method has to return self because of the way the old cpu-energy-meter was implemented,
        changing this would require changing the readout in every other file"""
        if not self.update_thread.is_alive() and not self.packages is None:
            return self
        self.stop_event.set()
        self.update_thread.join()
        if self.packages is None:
            return None
        return self

    def update_all(self):
        """this updates the counter for total energy consumed across all packages and domains"""
        for package in self.packages:
            package.update_value()

    def update_values(self):
        """this method is run by a thread to constantly sample energy values for overhead protection"""
        try:
            self.update_all()
            while not self.stop_event.wait(timeout=self.interval):
                self.update_all()
            self.update_all()
        except (OSError, ValueError, TypeError) as error:
            logging.error("Energy measurement failed")
            self.packages = None    #to prevent accidental accessing
            return

    def calculate_interval(self):
        """calculate measurement interval from short term power limit
        each package has various constraints numbered from 0, therefore we have to check
        each constraint name to find the number correlating to the short term limit
        Example limit file name would be "constraint_1_power_limit_uw
        We choose the smallest calculated interval as a worst case assumption"""
        intervals = []
        for package in self.packages:
            for constraint_name in package.path.glob("constraint_*_name"):
                if get_path_content(constraint_name) == "short_term":
                    constraint_prefix = constraint_name.name.removesuffix("_name")
                    constraint_value = int(
                        get_path_content(
                            package.path / f"{constraint_prefix}_power_limit_uw"
                        )
                    )
                    max_range = int(
                        get_path_content(package.path / "max_energy_range_uj")
                    )
                    if constraint_value == 0 or max_range == 0:
                        logging.debug(
                            "failed to read a constraint value for EnergyMeasurement"
                        )
                        return
                    intervals.append(max_range / constraint_value)

        if intervals != []:
            self.interval = min(intervals)

    def __str__(self):
        string = ""
        for package in self.packages:
            string += f"{package.name}: {package.energy.total} uj\n"
            for domain in package.domains:
                string += f"    {domain.name}: {domain.energy.total} uj\n"
        return string


def get_path_content(path):
    """if reading file fails the error event signals the thread that something went wrong
    and stops further measurement"""
    try:
        content = path.read_text().strip()
        return content
    except OSError as error:
        message = f"cannot read {path}: {error}"
        logging.debug(message)
        raise error
    # because the int() function throws a seperate error on None values


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
        if package.name != "psys":
            total += p_energy
            result[f"cpuenergy-{package.name}"] = p_energy
        else:
            result["systemenergy"] = p_energy
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
    print(f"interval: {measurement.interval}")
    print("starting measurement")
    measurement.interval = 1.0
    measurement.start()
    print(measurement)
    if len(sys.argv) < 2:
        sleep(10)
    else:
        subprocess.run(sys.argv[1:])
    result = measurement.stop()
    print(result)
    print(format_energy_results(result))
