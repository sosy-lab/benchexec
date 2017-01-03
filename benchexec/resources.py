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

"""
This module contains functions for computing assignments of resources to runs.
"""

# prepare for Python 3
from __future__ import absolute_import, division, print_function, unicode_literals

import collections
import itertools
import logging
import math
import os
import sys

from benchexec import cgroups
from benchexec import util

__all__ = [
           'check_memory_size',
           'get_cpu_cores_per_run',
           'get_memory_banks_per_run',
           ]

def get_cpu_cores_per_run(coreLimit, num_of_threads, my_cgroups):
    """
    Calculate an assignment of the available CPU cores to a number
    of parallel benchmark executions such that each run gets its own cores
    without overlapping of cores between runs.
    In case the machine has hyper-threading, this method tries to avoid
    putting two different runs on the same physical core
    (but it does not guarantee this if the number of parallel runs is too high to avoid it).
    In case the machine has multiple CPUs, this method avoids
    splitting a run across multiple CPUs if the number of cores per run
    is lower than the number of cores per CPU
    (splitting a run over multiple CPUs provides worse performance).
    It will also try to split the runs evenly across all available CPUs.

    A few theoretically-possible cases are not implemented,
    for example assigning three 10-core runs on a machine
    with two 16-core CPUs (this would have unfair core assignment
    and thus undesirable performance characteristics anyway).

    The list of available cores is read from the cgroup file system,
    such that the assigned cores are a subset of the cores
    that the current process is allowed to use.
    This script does currently not support situations
    where the available cores are asymmetrically split over CPUs,
    e.g. 3 cores on one CPU and 5 on another.

    @param coreLimit: the number of cores for each run
    @param num_of_threads: the number of parallel benchmark executions
    @return a list of lists, where each inner list contains the cores for one run
    """
    try:
        # read list of available CPU cores
        allCpus = util.parse_int_list(my_cgroups.get_value(cgroups.CPUSET, 'cpus'))
        logging.debug("List of available CPU cores is %s.", allCpus)

        # read mapping of core to CPU ("physical package")
        physical_packages = [int(util.read_file('/sys/devices/system/cpu/cpu{0}/topology/physical_package_id'.format(core))) for core in allCpus]
        cores_of_package = collections.defaultdict(list)
        for core, package in zip(allCpus, physical_packages):
            cores_of_package[package].append(core)
        logging.debug("Physical packages of cores are %s.", cores_of_package)

        # read hyper-threading information (sibling cores sharing the same physical core)
        siblings_of_core = {}
        for core in allCpus:
            siblings = util.parse_int_list(util.read_file('/sys/devices/system/cpu/cpu{0}/topology/thread_siblings_list'.format(core)))
            siblings_of_core[core] = siblings
        logging.debug("Siblings of cores are %s.", siblings_of_core)
    except ValueError as e:
        sys.exit("Could not read CPU information from kernel: {0}".format(e))

    return _get_cpu_cores_per_run0(coreLimit, num_of_threads, allCpus, cores_of_package, siblings_of_core)

def _get_cpu_cores_per_run0(coreLimit, num_of_threads, allCpus, cores_of_package, siblings_of_core):
    """This method does the actual work of _get_cpu_cores_per_run
    without reading the machine architecture from the file system
    in order to be testable. For description, c.f. above.
    Note that this method might change the input parameters!
    Do not call it directly, call getCpuCoresPerRun()!
    @param allCpus: the list of all available cores
    @param cores_of_package: a mapping from package (CPU) ids to lists of cores that belong to this CPU
    @param siblings_of_core: a mapping from each core to a list of sibling cores including the core itself (a sibling is a core sharing the same physical core)
    """
    # First, do some checks whether this algorithm has a chance to work.
    if coreLimit > len(allCpus):
        sys.exit("Cannot run benchmarks with {0} CPU cores, only {1} CPU cores available.".format(coreLimit, len(allCpus)))
    if coreLimit * num_of_threads > len(allCpus):
        sys.exit("Cannot run {0} benchmarks in parallel with {1} CPU cores each, only {2} CPU cores available. Please reduce the number of threads to {3}.".format(num_of_threads, coreLimit, len(allCpus), len(allCpus) // coreLimit))

    package_size = None # Number of cores per package
    for package, cores in cores_of_package.items():
        if package_size is None:
            package_size = len(cores)
        elif package_size != len(cores):
            sys.exit("Asymmetric machine architecture not supported: CPU package {0} has {1} cores, but other package has {2} cores.".format(package, len(cores), package_size))

    core_size = None # Number of threads per core
    for core, siblings in siblings_of_core.items():
        if core_size is None:
            core_size = len(siblings)
        elif core_size != len(siblings):
            sys.exit("Asymmetric machine architecture not supported: CPU core {0} has {1} siblings, but other core has {2} siblings.".format(core, len(siblings), core_size))

    all_cpus_set = set(allCpus)
    for core, siblings in siblings_of_core.items():
        siblings_set = set(siblings)
        if not siblings_set.issubset(all_cpus_set):
            sys.exit("Core assignment is unsupported because siblings {0} of core {1} are not usable. Please always make all virtual cores of a physical core available.".format(siblings_set.difference(all_cpus_set), core))

    # Second, compute some values we will need.
    package_count = len(cores_of_package)
    packages = sorted(cores_of_package.keys())
    coreLimit_rounded_up = int(math.ceil(coreLimit / core_size) * core_size)
    assert coreLimit <= coreLimit_rounded_up < (coreLimit + core_size)

    packages_per_run = int(math.ceil(coreLimit_rounded_up / package_size))
    if packages_per_run > 1 and packages_per_run * num_of_threads > package_count:
        sys.exit("Cannot split runs over multiple CPUs and at the same time assign multiple runs to the same CPU. Please reduce the number of threads to {0}.".format(package_count // packages_per_run))

    runs_per_package = int(math.ceil(num_of_threads / package_count))
    assert packages_per_run == 1 or runs_per_package == 1
    if packages_per_run == 1 and runs_per_package * coreLimit > package_size:
        sys.exit("Cannot run {} benchmarks with {} cores on {} CPUs with {} cores, because runs would need to be split across multiple CPUs. Please reduce the number of threads.".format(num_of_threads, coreLimit, package_count, package_size))

    # Warn on misuse of hyper-threading
    need_HT = False
    if packages_per_run == 1:
        # Checking whether the total amount of usable physical cores is not enough,
        # there might be some cores we cannot use, e.g. when scheduling with coreLimit=3 on quad-core machines.
        # Thus we check per package.
        assert coreLimit * runs_per_package <= package_size
        if coreLimit_rounded_up * runs_per_package > package_size:
            need_HT = True
            logging.warning("The number of threads is too high and hyper-threading sibling cores need to be split among different runs, which makes benchmarking unreliable. Please reduce the number of threads to %s.", (package_size // coreLimit_rounded_up) * package_count)

    else:
        if coreLimit_rounded_up * num_of_threads > len(allCpus):
            assert coreLimit_rounded_up * runs_per_package > package_size
            need_HT = True
            logging.warning("The number of threads is too high and hyper-threading sibling cores need to be split among different runs, which makes benchmarking unreliable. Please reduce the number of threads to %s.", len(allCpus) // coreLimit_rounded_up)

    logging.debug("Going to assign at most %s runs per package, each one using %s cores and blocking %s cores on %s packages.", runs_per_package, coreLimit, coreLimit_rounded_up, packages_per_run)

    # Third, do the actual core assignment.
    result = []
    used_cores = set()
    for run in range(num_of_threads):
        # this calculation ensures that runs are split evenly across packages
        start_package = (run * packages_per_run) % package_count
        cores = []
        cores_with_siblings = set()
        for package_nr in range(start_package, start_package + packages_per_run):
            assert len(cores) < coreLimit
            # Some systems have non-contiguous package numbers,
            # so we take the i'th package out of the list of available packages.
            # On normal system this is the identity mapping.
            package = packages[package_nr]
            for core in cores_of_package[package]:
                if core not in cores:
                    cores.extend(c for c in siblings_of_core[core] if not c in used_cores)
                if len(cores) >= coreLimit:
                    break
            cores_with_siblings.update(cores)
            cores = cores[:coreLimit] # shrink if we got more cores than necessary
            # remove used cores such that we do not try to use them again
            cores_of_package[package] = [core for core in cores_of_package[package] if core not in cores]

        assert len(cores) == coreLimit, "Wrong number of cores for run {} of {} - previous results: {}, remaining cores per package: {}, current cores: {}".format(run+1, num_of_threads, result, cores_of_package, cores)
        blocked_cores = cores if need_HT else cores_with_siblings
        assert not used_cores.intersection(blocked_cores)
        used_cores.update(blocked_cores)
        result.append(sorted(cores))

    assert len(result) == num_of_threads
    assert all(len(cores) == coreLimit for cores in result)
    assert len(set(itertools.chain(*result))) == num_of_threads * coreLimit, "Cores are not uniquely assigned to runs: " + result

    logging.debug("Final core assignment: %s.", result)
    return result


def get_memory_banks_per_run(coreAssignment, cgroups):
    """Get an assignment of memory banks to runs that fits to the given coreAssignment,
    i.e., no run is allowed to use memory that is not local (on the same NUMA node)
    to one of its CPU cores."""
    try:
        # read list of available memory banks
        allMems = set(cgroups.read_allowed_memory_banks())

        result = []
        for cores in coreAssignment:
            mems = set()
            for core in cores:
                coreDir = '/sys/devices/system/cpu/cpu{0}/'.format(core)
                mems.update(_get_memory_banks_listed_in_dir(coreDir))
            allowedMems = sorted(mems.intersection(allMems))
            logging.debug("Memory banks for cores %s are %s, of which we can use %s.", cores, list(mems), allowedMems)

            result.append(allowedMems)

        assert len(result) == len(coreAssignment)

        if any(result) and os.path.isdir('/sys/devices/system/node/'):
            return result
        else:
            # All runs get the empty list of memory regions
            # because this system has no NUMA support
            return None
    except ValueError as e:
        sys.exit("Could not read memory information from kernel: {0}".format(e))


def _get_memory_banks_listed_in_dir(path):
    """Get all memory banks the kernel lists in a given directory.
    Such a directory can be /sys/devices/system/node/ (contains all memory banks)
    or /sys/devices/system/cpu/cpu*/ (contains all memory banks on the same NUMA node as that core)."""
    # Such directories contain entries named "node<id>" for each memory bank
    return [int(entry[4:]) for entry in os.listdir(path) if entry.startswith('node')]


def check_memory_size(memLimit, num_of_threads, memoryAssignment, my_cgroups):
    """Check whether the desired amount of parallel benchmarks fits in the memory.
    Implemented are checks for memory limits via cgroup controller "memory" and
    memory bank restrictions via cgroup controller "cpuset",
    as well as whether the system actually has enough memory installed.
    @param memLimit: the memory limit in bytes per run
    @param num_of_threads: the number of parallel benchmark executions
    @param memoryAssignment: the allocation of memory banks to runs (if not present, all banks are assigned to all runs)
    """
    try:
        # Check amount of memory allowed via cgroups.
        def check_limit(actualLimit):
            if actualLimit < memLimit:
                sys.exit("Cgroups allow only {} bytes of memory to be used, cannot execute runs with {} bytes of memory.".format(actualLimit, memLimit))
            elif actualLimit < memLimit * num_of_threads:
                sys.exit("Cgroups allow only {} bytes of memory to be used, not enough for {} benchmarks with {} bytes each. Please reduce the number of threads".format(actualLimit, num_of_threads, memLimit))

        if not os.path.isdir('/sys/devices/system/node/'):
            logging.debug("System without NUMA support in Linux kernel, ignoring memory assignment.")
            return

        if cgroups.MEMORY in my_cgroups:
            # We use the entries hierarchical_*_limit in memory.stat and not memory.*limit_in_bytes
            # because the former may be lower if memory.use_hierarchy is enabled.
            for key, value in my_cgroups.get_key_value_pairs(cgroups.MEMORY, 'stat'):
                if key == 'hierarchical_memory_limit' or key == 'hierarchical_memsw_limit':
                    check_limit(int(value))

        # Get list of all memory banks, either from memory assignment or from system.
        if not memoryAssignment:
            if cgroups.CPUSET in my_cgroups:
                allMems = my_cgroups.read_allowed_memory_banks()
            else:
                allMems = _get_memory_banks_listed_in_dir('/sys/devices/system/node/')
            memoryAssignment = [allMems] * num_of_threads # "fake" memory assignment: all threads on all banks
        else:
            allMems = set(itertools.chain(*memoryAssignment))

        memSizes = dict((mem, _get_memory_bank_size(mem)) for mem in allMems)
    except ValueError as e:
        sys.exit("Could not read memory information from kernel: {0}".format(e))

    # Check whether enough memory is allocatable on the assigned memory banks.
    # As the sum of the sizes of the memory banks is at most the total size of memory in the system,
    # and we do this check always even if the banks are not restricted,
    # this also checks whether the system has actually enough memory installed.
    usedMem = collections.Counter()
    for mems_of_run in memoryAssignment:
        totalSize = sum(memSizes[mem] for mem in mems_of_run)
        if totalSize < memLimit:
            sys.exit("Memory banks {} do not have enough memory for one run, only {} bytes available.".format(mems_of_run, totalSize))
        usedMem[tuple(mems_of_run)] += memLimit
        if usedMem[tuple(mems_of_run)] > totalSize:
            sys.exit("Memory banks {} do not have enough memory for all runs, only {} bytes available. Please reduce the number of threads.".format(mems_of_run, totalSize))

def _get_memory_bank_size(memBank):
    """Get the size of a memory bank in bytes."""
    fileName = '/sys/devices/system/node/node{0}/meminfo'.format(memBank)
    size = None
    with open(fileName) as f:
        for line in f:
            if 'MemTotal' in line:
                size = line.split(':')[1].strip()
                if size[-3:] != ' kB':
                    raise ValueError('"{}" in file {} is not a memory size.'.format(size, fileName))
                size = int(size[:-3]) * 1024 # kernel uses KiB but names them kB, convert to Byte
                logging.debug("Memory bank %s has size %s bytes.", memBank, size)
                return size
    raise ValueError('Failed to read total memory from {}.'.format(fileName))
