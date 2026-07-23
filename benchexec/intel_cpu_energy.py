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
        p for p in rapl_path.glob("intel-rapl:*")
        if p.name.count(":") == 1):
            p_name = (package/"name").read_text().strip()
            domains = []
            for domain in sorted(
            d for d in package.glob("intel-rapl:*")
            if d.name.count(":") == 2):
                d_name = (domain/"name").read_text().strip()
                domains.append(Domain(d_name, domain, 0))

            self.packages.append(Package(p_name, package, 0, domains))

    @classmethod
    def create_if_supported(cls):
        if not rapl_path.exists():
            logging.debug("Intel RAPL Kernel module for energy measurement not available, try \"modprobe intel-rapl-msr\"")
            return None
        return cls()

    def start(self):
        for package in self.packages:
            package.energy = int((package.path/"energy_uj").read_text().strip())
            for domain in package.domains:
                domain.energy = int((domain.path/"energy_uj").read_text().strip())
        self.running = True

    def stop(self):
        if not self.running:
            return self

        for package in self.packages:
            package.energy = int((package.path/"energy_uj").read_text().strip()) - package.energy
            for domain in package.domains:
                domain.energy = int((domain.path/"energy_uj").read_text().strip()) - domain.energy
        self.running = False
        return self

    def __str__(self):
        string = ""
        for package in self.packages:
            string += f"{package.name}: {package.energy} uj\n"
            for domain in package.domains:
                string += f"    {domain.name}: {domain.energy} uj\n"
        return string
    

def format_energy_results(measurement):
    if not measurement:
        return {}
    result = {}
    total = Decimal(0)
    for package in measurement.packages:
        p_energy = Decimal(package.energy) / Decimal(1000000)
        if not package.name.__eq__("psys"):
            total += p_energy
            result[f"cpuenergy-{package.name}"] = p_energy
        else:
            result["psys"] = p_energy
        for domain in package.domains:
            d_energy = Decimal(domain.energy) / Decimal(1000000)
            result[f"cpuenergy-{package.name}-{domain.name}"] = d_energy
    result["cpuenergy"] = total
    result = collections.OrderedDict(sorted(result.items()))
    return result
