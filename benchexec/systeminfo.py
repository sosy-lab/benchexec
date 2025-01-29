# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

"""
This module allows to retrieve information about the current system.
"""

from decimal import Decimal
import glob
import logging
import os
import platform
import sys

from benchexec import util

__all__ = [
    "has_swap",
    "is_turbo_boost_enabled",
    "CPUThrottleCheck",
    "SystemInfo",
    "SwapCheck",
]

_TURBO_BOOST_FILE = "/sys/devices/system/cpu/cpufreq/boost"
_TURBO_BOOST_FILE_PSTATE = "/sys/devices/system/cpu/intel_pstate/no_turbo"


class SystemInfo(object):
    def __init__(self):
        """
        This function finds some information about the computer.
        """
        # get info about OS
        self.hostname = platform.node()
        self.os = platform.platform(aliased=True)

        # get info about CPU
        cpuInfo = {}
        self.cpu_max_frequency = "unknown"
        cpuInfoFilename = "/proc/cpuinfo"
        self.cpu_number_of_cores = "unknown"
        if os.path.isfile(cpuInfoFilename) and os.access(cpuInfoFilename, os.R_OK):
            cpuInfoFile = open(cpuInfoFilename, "rt")
            cpuInfoLines = [
                tuple(line.split(":"))
                for line in cpuInfoFile.read()
                .replace("\n\n", "\n")
                .replace("\t", "")
                .strip("\n")
                .split("\n")
            ]
            cpuInfo = dict(cpuInfoLines)
            cpuInfoFile.close()
            self.cpu_number_of_cores = str(
                len([line for line in cpuInfoLines if line[0] == "processor"])
            )
        self.cpu_model = (
            cpuInfo.get("model name", "unknown")
            .strip()
            .replace("(R)", "")
            .replace("(TM)", "")
            .replace("(tm)", "")
        )
        if "cpu MHz" in cpuInfo:
            freq_hz = Decimal(cpuInfo["cpu MHz"]) * 1000 * 1000  # convert to Hz
            self.cpu_max_frequency = int((freq_hz).to_integral_value())

        # Modern CPUs do not have a constant frequency and can be limited.
        # We want the maximum frequency that the CPU could use,
        # and if we can read it we will overwrite the value from above.
        freqInfoFilename = "/sys/devices/system/cpu/cpu0/cpufreq/scaling_max_freq"
        cpu_max_frequency = util.try_read_file(freqInfoFilename)
        if cpu_max_frequency:
            self.cpu_max_frequency = int(cpu_max_frequency) * 1000  # convert to Hz

        self.cpu_turboboost = is_turbo_boost_enabled()

        # get info about memory
        memInfo = {}
        memInfoFilename = "/proc/meminfo"
        if os.path.isfile(memInfoFilename) and os.access(memInfoFilename, os.R_OK):
            memInfoFile = open(memInfoFilename, "rt")
            memInfo = dict(
                tuple(s.split(": "))
                for s in memInfoFile.read().replace("\t", "").strip("\n").split("\n")
            )
            memInfoFile.close()
        self.memory = memInfo.get("MemTotal", "unknown").strip()
        if self.memory.endswith(" kB"):
            # kernel uses KiB but names them kB, convert to Byte
            self.memory = int(self.memory[:-3]) * 1024

        self.environment = os.environ.copy()
        # The following variables are overridden by runexec anyway.
        self.environment.pop("HOME", None)
        self.environment.pop("TMPDIR", None)
        self.environment.pop("TMP", None)
        self.environment.pop("TEMPDIR", None)
        self.environment.pop("TEMP", None)


class CPUThrottleCheck(object):
    """
    Class for checking whether the CPU has throttled during some time period.
    """

    def __init__(self, cores=None):
        """
        Create an instance that monitors the given list of cores (or all CPUs).
        """
        self.cpu_throttle_count = {}
        cores = [str(core) for core in cores] if cores else ["*"]
        for core in cores:
            for file in glob.iglob(
                f"/sys/devices/system/cpu/cpu{core}/thermal_throttle/*_throttle_count"
            ):
                try:
                    self.cpu_throttle_count[file] = int(util.read_file(file))
                except Exception as e:
                    logging.warning(
                        "Cannot read throttling count of CPU from kernel: %s", e
                    )

    def has_throttled(self):
        """
        Check whether any of the CPU cores monitored by this instance has
        throttled since this instance was created.
        @return a boolean value
        """
        for file, value in self.cpu_throttle_count.items():
            try:
                new_value = int(util.read_file(file))
                if new_value > value:
                    return True
            except Exception as e:
                logging.warning(
                    "Cannot read throttling count of CPU from kernel: %s", e
                )
        return False


class SwapCheck(object):
    """
    Class for checking whether the system has swapped during some period.
    """

    def __init__(self):
        self.swap_count = self._read_swap_count()

    def _read_swap_count(self):
        try:
            return {
                k: int(v)
                for k, v in util.read_key_value_pairs_from_file("/proc/vmstat")
                if k in ["pswpin", "pswpout"]
            }
        except Exception as e:
            logging.warning("Cannot read swap count from kernel: %s", e)

    def has_swapped(self):
        """
        Check whether any swapping occured on this system since this instance was created.
        @return a boolean value
        """
        new_values = self._read_swap_count()
        for key, new_value in new_values.items():
            old_value = self.swap_count.get(key, 0)
            if new_value > old_value:
                return True
        return False


def is_turbo_boost_enabled():
    """
    Check whether Turbo Boost (scaling CPU frequency beyond nominal frequency)
    is active on this system.
    @return: A bool, or None if Turbo Boost is not supported.
    """
    try:
        if os.path.exists(_TURBO_BOOST_FILE):
            boost_enabled = int(util.read_file(_TURBO_BOOST_FILE))
            if not (0 <= boost_enabled <= 1):
                raise ValueError(
                    f"Invalid value {boost_enabled} for turbo boost activation"
                )
            return boost_enabled != 0
        if os.path.exists(_TURBO_BOOST_FILE_PSTATE):
            boost_disabled = int(util.read_file(_TURBO_BOOST_FILE_PSTATE))
            if not (0 <= boost_disabled <= 1):
                raise ValueError(
                    f"Invalid value {boost_disabled} for turbo boost activation"
                )
            return boost_disabled != 1
    except ValueError as e:
        sys.exit(f"Could not read turbo-boost information from kernel: {e}")


def has_swap():
    with open("/proc/meminfo", "r") as meminfo:
        for line in meminfo:
            if line.startswith("SwapTotal:"):
                swap = line.split()[1]
                if int(swap) == 0:
                    return False
    return True


def is_debian():
    """Try to detect whether the current system is a Debian or derivative like Ubuntu"""
    try:
        with open("/etc/os-release") as f:
            return any(
                (line.startswith("ID=") or line.startswith("ID_LIKE="))
                and "debian" in line
                for line in f.readlines()
            )
    except OSError:
        return False


def has_systemd():
    """Try to detect whether the current system is running systemd as init system."""
    return os.path.isdir("/run/systemd/system")
