"""
BenchExec is a framework for reliable benchmarking.
This file is part of BenchExec.

Copyright (C) 2007-2015  Dirk Beyer
All rights reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

# prepare for Python 3
from __future__ import absolute_import, division, print_function, unicode_literals

"""
This module allows to retrieve information about the current system.
"""

import os
import sys

from . import util

__all__ = [
           'has_swap',
           'is_turbo_boost_enabled',
           'SystemInfo',
           ]

_TURBO_BOOST_FILE = "/sys/devices/system/cpu/cpufreq/boost"
_TURBO_BOOST_FILE_PSTATE = "/sys/devices/system/cpu/intel_pstate/no_turbo"

class SystemInfo(object):
    def __init__(self):
        """
        This function finds some information about the computer.
        """
        # get info about OS
        (sysname, self.hostname, kernel, version, machine) = os.uname()  # @UnusedVariable
        self.os = sysname + " " + kernel + " " + machine

        # get info about CPU
        cpuInfo = dict()
        self.cpu_max_frequency = 'unknown'
        cpuInfoFilename = '/proc/cpuinfo'
        self.cpu_number_of_cores = 'unknown'
        if os.path.isfile(cpuInfoFilename) and os.access(cpuInfoFilename, os.R_OK):
            cpuInfoFile = open(cpuInfoFilename, 'rt')
            cpuInfoLines = [tuple(line.split(':')) for line in
                            cpuInfoFile.read()
                                       .replace('\n\n', '\n').replace('\t', '')
                                       .strip('\n').split('\n')]
            cpuInfo = dict(cpuInfoLines)
            cpuInfoFile.close()
            self.cpu_number_of_cores = str(len([line for line in cpuInfoLines if line[0] == 'processor']))
        self.cpu_model = cpuInfo.get('model name', 'unknown') \
                               .strip() \
                               .replace("(R)", "") \
                               .replace("(TM)", "") \
                               .replace("(tm)", "")
        if 'cpu MHz' in cpuInfo:
            self.cpu_max_frequency = cpuInfo['cpu MHz'].split('.')[0].strip() + ' MHz'

        # modern cpus may not work with full speed the whole day
        # read the number from cpufreq and overwrite cpu_max_frequency from above
        freqInfoFilename = '/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq'
        if os.path.isfile(freqInfoFilename) and os.access(freqInfoFilename, os.R_OK):
            frequencyInfoFile = open(freqInfoFilename, 'rt')
            cpu_max_frequency = frequencyInfoFile.read().strip('\n')
            frequencyInfoFile.close()
            self.cpu_max_frequency = str(int(cpu_max_frequency) // 1000) + ' MHz'

        self.cpu_turboboost = is_turbo_boost_enabled()

        # get info about memory
        memInfo = dict()
        memInfoFilename = '/proc/meminfo'
        if os.path.isfile(memInfoFilename) and os.access(memInfoFilename, os.R_OK):
            memInfoFile = open(memInfoFilename, 'rt')
            memInfo = dict(tuple(s.split(': ')) for s in
                            memInfoFile.read()
                            .replace('\t', '')
                            .strip('\n').split('\n'))
            memInfoFile.close()
        self.memory = memInfo.get('MemTotal', 'unknown').strip()

        self.environment = os.environ.copy()

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
                raise ValueError('Invalid value {} for turbo boost activation'.format(boost_enabled))
            return boost_enabled != 0
        if os.path.exists(_TURBO_BOOST_FILE_PSTATE):
            boost_disabled = int(util.read_file(_TURBO_BOOST_FILE_PSTATE))
            if not (0 <= boost_disabled <= 1):
                raise ValueError('Invalid value {} for turbo boost activation'.format(boost_enabled))
            return boost_disabled != 1
    except ValueError as e:
        sys.exit("Could not read turbo-boost information from kernel: {0}".format(e))


def has_swap():
    with open('/proc/meminfo', 'r') as meminfo:
        for line in meminfo:
            if line.startswith('SwapTotal:'):
                swap = line.split()[1]
                if int(swap) == 0:
                    return False
    return True