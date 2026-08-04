# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

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
class Domain:
    name: str
    path: Path
    energy: int


@dataclass
class Package:
    name: str
    path: Path
    energy: int
    domains: list[Domain]


class EnergyMeasurement(object):
    def __init__(self):
        self.running = False
        self.packages: list[Package] = []
        for package in sorted(
            p for p in rapl_path.glob("intel-rapl:*") if p.name.count(":") == 1
        ):
            p_name = (package / "name").read_text().strip()
            domains = []
            for domain in sorted(
                d for d in package.glob("intel-rapl:*") if d.name.count(":") == 2
            ):
                d_name = (domain / "name").read_text().strip()
                domains.append(Domain(d_name, domain, 0))

            self.packages.append(Package(p_name, package, 0, domains))

    @classmethod
    def create_if_supported(cls):
        if not rapl_path.exists():
            logging.debug(
                'Intel RAPL Kernel module for energy measurement not available, try "modprobe intel-rapl-msr"'
            )
            return None
        return cls()

    def start(self):
        """Start the measruement by reading initial values"""
        for package in self.packages:
            package.energy = int((package.path / "energy_uj").read_text().strip())
            for domain in package.domains:
                domain.energy = int((domain.path / "energy_uj").read_text().strip())
        self.running = True

    def stop(self):
        """Stop the measurement if it hasn't been stopped already
        This method has to return self because of the way the old cpu-energy-meter was implemented,
        changing this would require changing the readout in every other file"""
        if not self.running:
            return self

        for package in self.packages:
            package.energy = (
                int((package.path / "energy_uj").read_text().strip()) - package.energy
            )
            for domain in package.domains:
                domain.energy = (
                    int((domain.path / "energy_uj").read_text().strip()) - domain.energy
                )
        self.running = False
        return self

    def __str__(self):
        string = ""
        for package in self.packages:
            string += f"{package.name}: {package.energy} uj\n"
            for domain in package.domains:
                string += f"    {domain.name}: {domain.energy} uj\n"
        return string


def convert_to_joules(energy):
    """The values read from the energy_uj file are in microjoules and need to be converted to joules"""
    return Decimal(energy) / Decimal(1000000)


def format_energy_results(measurement):
    """Take the result of an energy measurement and return a flat dictionary that contains all values."""
    if not measurement:
        return {}
    result = {}
    total = Decimal(0)
    for package in measurement.packages:
        p_energy = convert_to_joules(package.energy)
        if not package.name == "psys":
            total += p_energy
            result[f"cpuenergy-{package.name}"] = p_energy
        else:
            result["psys"] = p_energy
        for domain in package.domains:
            d_energy = convert_to_joules(domain.energy)
            result[f"cpuenergy-{package.name}-{domain.name}"] = d_energy
    result["cpuenergy"] = total
    result = collections.OrderedDict(sorted(result.items()))
    return result


if __name__ == "__main__":
    measurement = EnergyMeasurement.create_if_supported()
    print("starting measurement")
    measurement.start()
    if len(sys.argv) < 2:
        sleep(3)
    else:
        subprocess.run(sys.argv[1:])
    measurement.stop()
    print(measurement)
    print(format_energy_results(measurement))
