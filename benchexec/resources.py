# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

"""
This module contains functions for computing assignments of resources to runs.
"""

import collections
import itertools
import logging
import math
import os
import sys

from benchexec import util

__all__ = [
    "check_memory_size",
    "get_cpu_cores_per_run",
    "get_memory_banks_per_run",
    "get_cpu_package_for_core",
]


def get_cpu_cores_per_run(
    coreLimit, num_of_threads, use_hyperthreading, my_cgroups, coreSet=None
):
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
    @param coreSet: the list of CPU cores identifiers provided by a user, None makes benchexec using all cores
    @return a list of lists, where each inner list contains the cores for one run
    """
    try:
        # read list of available CPU cores
        allCpus = my_cgroups.read_allowed_cpus()

        # Filter CPU cores according to the list of identifiers provided by a user
        if coreSet:
            invalid_cores = sorted(set(coreSet).difference(set(allCpus)))
            if len(invalid_cores) > 0:
                raise ValueError(
                    "The following provided CPU cores are not available: "
                    + ", ".join(map(str, invalid_cores))
                )
            allCpus = [core for core in allCpus if core in coreSet]

        logging.debug("List of available CPU cores is %s.", allCpus)

        # read mapping of core to memory region
        cores_of_memory_region = collections.defaultdict(list)
        for core in allCpus:
            coreDir = f"/sys/devices/system/cpu/cpu{core}/"
            memory_regions = _get_memory_banks_listed_in_dir(coreDir)
            if memory_regions:
                cores_of_memory_region[memory_regions[0]].append(core)
            else:
                # If some cores do not have NUMA information, skip using it completely
                logging.warning(
                    "Kernel does not have NUMA support. Use benchexec at your own risk."
                )
                cores_of_memory_region = {}
                break
        logging.debug("Memory regions of cores are %s.", cores_of_memory_region)

        # read mapping of core to CPU ("physical package")
        cores_of_package = collections.defaultdict(list)
        for core in allCpus:
            package = get_cpu_package_for_core(core)
            cores_of_package[package].append(core)
        logging.debug("Physical packages of cores are %s.", cores_of_package)

        # select the more fine grained division among memory regions and physical package
        if len(cores_of_memory_region) >= len(cores_of_package):
            cores_of_unit = cores_of_memory_region
            logging.debug("Using memory regions as the basis for cpu core division")
        else:
            cores_of_unit = cores_of_package
            logging.debug("Using physical packages as the basis for cpu core division")

        # read hyper-threading information (sibling cores sharing the same physical core)
        siblings_of_core = {}
        for core in allCpus:
            siblings = util.parse_int_list(
                util.read_file(
                    f"/sys/devices/system/cpu/cpu{core}/topology/thread_siblings_list"
                )
            )
            siblings_of_core[core] = siblings
        logging.debug("Siblings of cores are %s.", siblings_of_core)
    except ValueError as e:
        sys.exit(f"Could not read CPU information from kernel: {e}")
    return _get_cpu_cores_per_run0(
        coreLimit,
        num_of_threads,
        use_hyperthreading,
        allCpus,
        cores_of_unit,
        siblings_of_core,
    )


def _get_cpu_cores_per_run0(
    coreLimit,
    num_of_threads,
    use_hyperthreading,
    allCpus,
    cores_of_unit,
    siblings_of_core,
):
    """This method does the actual work of _get_cpu_cores_per_run
    without reading the machine architecture from the file system
    in order to be testable. For description, c.f. above.
    Note that this method might change the input parameters!
    Do not call it directly, call getCpuCoresPerRun()!
    @param use_hyperthreading: A boolean to check if no-hyperthreading method is being used
    @param allCpus: the list of all available cores
    @param cores_of_unit: a mapping from logical unit (can be memory region (NUMA node) or physical package(CPU), depending on the architecture of system)
                          to lists of cores that belong to this unit
    @param siblings_of_core: a mapping from each core to a list of sibling cores including the core itself (a sibling is a core sharing the same physical core)
    """
    # First, do some checks whether this algorithm has a chance to work.
    coreCount = len(allCpus)
    if coreLimit > coreCount:
        sys.exit(
            f"Cannot run benchmarks with {coreLimit} CPU cores, "
            f"only {coreCount} CPU cores available."
        )
    if coreLimit * num_of_threads > coreCount:
        sys.exit(
            f"Cannot run {num_of_threads} benchmarks in parallel "
            f"with {coreLimit} CPU cores each, only {coreCount} CPU cores available. "
            f"Please reduce the number of threads to {coreCount // coreLimit}."
        )

    if not use_hyperthreading:
        unit_of_core = {}
        unused_cores = []
        for unit, cores in cores_of_unit.items():
            for core in cores:
                unit_of_core[core] = unit
        for core, siblings in siblings_of_core.items():
            if core in allCpus:
                siblings.remove(core)
                cores_of_unit[unit_of_core[core]] = [
                    c for c in cores_of_unit[unit_of_core[core]] if c not in siblings
                ]
                siblings_of_core[core] = [core]
                allCpus = [c for c in allCpus if c not in siblings]
            else:
                unused_cores.append(core)
        for core in unused_cores:
            siblings_of_core.pop(core)
        logging.debug(
            "Running in no-hyperthreading mode, avoiding the use of CPU cores %s",
            unused_cores,
        )

    unit_size = len(next(iter(cores_of_unit.values())))  # Number of units per core
    if any(len(cores) != unit_size for cores in cores_of_unit.values()):
        sys.exit(
            "Asymmetric machine architecture not supported: "
            "CPUs/memory regions with different number of cores."
        )

    core_size = len(next(iter(siblings_of_core.values())))  # Number of threads per core
    if any(len(siblings) != core_size for siblings in siblings_of_core.values()):
        sys.exit(
            "Asymmetric machine architecture not supported: "
            "CPU cores with different number of sibling cores."
        )

    all_cpus_set = set(allCpus)
    for core, siblings in siblings_of_core.items():
        siblings_set = set(siblings)
        if not siblings_set.issubset(all_cpus_set):
            unusable_cores = siblings_set.difference(all_cpus_set)
            sys.exit(
                f"Core assignment is unsupported because siblings {unusable_cores} "
                f"of core {core} are not usable. "
                f"Please always make all virtual cores of a physical core available."
            )

    # Second, compute some values we will need.
    unit_count = len(cores_of_unit)
    units = sorted(cores_of_unit.keys())
    coreLimit_rounded_up = int(math.ceil(coreLimit / core_size) * core_size)
    assert coreLimit <= coreLimit_rounded_up < (coreLimit + core_size)

    units_per_run = int(math.ceil(coreLimit_rounded_up / unit_size))
    if units_per_run > 1 and units_per_run * num_of_threads > unit_count:
        sys.exit(
            f"Cannot split runs over multiple CPUs/memory regions "
            f"and at the same time assign multiple runs to the same CPU/memory region. "
            f"Please reduce the number of threads to {unit_count // units_per_run}."
        )

    runs_per_unit = int(math.ceil(num_of_threads / unit_count))
    assert units_per_run == 1 or runs_per_unit == 1
    if units_per_run == 1 and runs_per_unit * coreLimit > unit_size:
        sys.exit(
            f"Cannot run {num_of_threads} benchmarks with {coreLimit} cores "
            f"on {unit_count} CPUs/memory regions with {unit_size} cores, "
            f"because runs would need to be split across multiple CPUs/memory regions. "
            f"Please reduce the number of threads."
        )

    # Warn on misuse of hyper-threading
    need_HT = False
    if units_per_run == 1:
        # Checking whether the total amount of usable physical cores is not enough,
        # there might be some cores we cannot use, e.g. when scheduling with coreLimit=3 on quad-core machines.
        # Thus we check per unit.
        assert coreLimit * runs_per_unit <= unit_size
        if coreLimit_rounded_up * runs_per_unit > unit_size:
            need_HT = True
            logging.warning(
                "The number of threads is too high and hyper-threading sibling cores need to be split among different runs, which makes benchmarking unreliable. Please reduce the number of threads to %s.",
                (unit_size // coreLimit_rounded_up) * unit_count,
            )

    else:
        if coreLimit_rounded_up * num_of_threads > len(allCpus):
            assert coreLimit_rounded_up * runs_per_unit > unit_size
            need_HT = True
            logging.warning(
                "The number of threads is too high and hyper-threading sibling cores need to be split among different runs, which makes benchmarking unreliable. Please reduce the number of threads to %s.",
                len(allCpus) // coreLimit_rounded_up,
            )

    logging.debug(
        "Going to assign at most %s runs per CPU/memory region, each one using %s cores and blocking %s cores on %s CPUs/memory regions.",
        runs_per_unit,
        coreLimit,
        coreLimit_rounded_up,
        units_per_run,
    )

    # Third, do the actual core assignment.
    result = []
    used_cores = set()
    for run in range(num_of_threads):
        # this calculation ensures that runs are split evenly across units
        start_unit = (run * units_per_run) % unit_count
        cores = []
        cores_with_siblings = set()
        for unit_nr in range(start_unit, start_unit + units_per_run):
            assert len(cores) < coreLimit
            # Some systems have non-contiguous unit numbers,
            # so we take the i'th unit out of the list of available units.
            # On normal system this is the identity mapping.
            unit = units[unit_nr]
            for core in cores_of_unit[unit]:
                if core not in cores:
                    cores.extend(
                        c for c in siblings_of_core[core] if c not in used_cores
                    )
                if len(cores) >= coreLimit:
                    break
            cores_with_siblings.update(cores)
            cores = cores[:coreLimit]  # shrink if we got more cores than necessary
            # remove used cores such that we do not try to use them again
            cores_of_unit[unit] = [
                core for core in cores_of_unit[unit] if core not in cores
            ]

        assert len(cores) == coreLimit, (
            f"Wrong number of cores for run {run + 1} of {num_of_threads} "
            f"- previous results: {result}, "
            f"remaining cores per CPU/memory region: {cores_of_unit}, "
            f"current cores: {cores}"
        )
        blocked_cores = cores if need_HT else cores_with_siblings
        assert not used_cores.intersection(blocked_cores)
        used_cores.update(blocked_cores)
        result.append(sorted(cores))

    assert len(result) == num_of_threads
    assert all(len(cores) == coreLimit for cores in result)
    assert (
        len(set(itertools.chain(*result))) == num_of_threads * coreLimit
    ), f"Cores are not uniquely assigned to runs: {result}"

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
                coreDir = f"/sys/devices/system/cpu/cpu{core}/"
                mems.update(_get_memory_banks_listed_in_dir(coreDir))
            allowedMems = sorted(mems.intersection(allMems))
            logging.debug(
                "Memory banks for cores %s are %s, of which we can use %s.",
                cores,
                list(mems),
                allowedMems,
            )

            result.append(allowedMems)

        assert len(result) == len(coreAssignment)

        if any(result) and os.path.isdir("/sys/devices/system/node/"):
            return result
        else:
            # All runs get the empty list of memory regions
            # because this system has no NUMA support
            return None
    except ValueError as e:
        sys.exit(f"Could not read memory information from kernel: {e}")


def _get_memory_banks_listed_in_dir(path):
    """Get all memory banks the kernel lists in a given directory.
    Such a directory can be /sys/devices/system/node/ (contains all memory banks)
    or /sys/devices/system/cpu/cpu*/ (contains all memory banks on the same NUMA node as that core).
    """
    # Such directories contain entries named "node<id>" for each memory bank
    return [int(entry[4:]) for entry in os.listdir(path) if entry.startswith("node")]


def check_memory_size(memLimit, num_of_threads, memoryAssignment, my_cgroups):
    """Check whether the desired amount of parallel benchmarks fits in the memory.
    Implemented are checks for memory limits via cgroup subsystem "memory" and
    memory bank restrictions via cgroup subsystem "cpuset",
    as well as whether the system actually has enough memory installed.
    @param memLimit: the memory limit in bytes per run
    @param num_of_threads: the number of parallel benchmark executions
    @param memoryAssignment: the allocation of memory banks to runs (if not present, all banks are assigned to all runs)
    """
    try:
        # Check amount of memory allowed via cgroups.
        def check_limit(actualLimit):
            if actualLimit < memLimit:
                sys.exit(
                    f"Cgroups allow only {actualLimit} bytes of memory to be used, "
                    f"cannot execute runs with {memLimit} bytes of memory."
                )
            elif actualLimit < memLimit * num_of_threads:
                sys.exit(
                    f"Cgroups allow only {actualLimit} bytes of memory to be used, "
                    f"not enough for {num_of_threads} benchmarks with {memLimit} bytes "
                    f"each. Please reduce the number of threads."
                )

        if not os.path.isdir("/sys/devices/system/node/"):
            logging.debug(
                "System without NUMA support in Linux kernel, ignoring memory assignment."
            )
            return

        if my_cgroups.MEMORY in my_cgroups:
            actual_limit = my_cgroups.read_hierarchical_memory_limit()
            if actual_limit is not None:
                check_limit(actual_limit)

        # Get list of all memory banks, either from memory assignment or from system.
        if not memoryAssignment:
            if my_cgroups.CPUSET in my_cgroups:
                allMems = my_cgroups.read_allowed_memory_banks()
            else:
                allMems = _get_memory_banks_listed_in_dir("/sys/devices/system/node/")
            memoryAssignment = [
                allMems
            ] * num_of_threads  # "fake" memory assignment: all threads on all banks
        else:
            allMems = set(itertools.chain(*memoryAssignment))

        memSizes = {mem: _get_memory_bank_size(mem) for mem in allMems}
    except ValueError as e:
        sys.exit(f"Could not read memory information from kernel: {e}")

    # Check whether enough memory is allocatable on the assigned memory banks.
    # As the sum of the sizes of the memory banks is at most the total size of memory in the system,
    # and we do this check always even if the banks are not restricted,
    # this also checks whether the system has actually enough memory installed.
    usedMem = collections.Counter()
    for mems_of_run in memoryAssignment:
        totalSize = sum(memSizes[mem] for mem in mems_of_run)
        if totalSize < memLimit:
            sys.exit(
                f"Memory banks {mems_of_run} do not have enough memory for one run, "
                f"only {totalSize} bytes available."
            )
        usedMem[tuple(mems_of_run)] += memLimit
        if usedMem[tuple(mems_of_run)] > totalSize:
            sys.exit(
                f"Memory banks {mems_of_run} do not have enough memory for all runs, "
                f"only {totalSize} bytes available. Please reduce the number of threads."
            )


def _get_memory_bank_size(memBank):
    """Get the size of a memory bank in bytes."""
    fileName = f"/sys/devices/system/node/node{memBank}/meminfo"
    size = None
    with open(fileName) as f:
        for line in f:
            if "MemTotal" in line:
                size = line.split(":")[1].strip()
                if size[-3:] != " kB":
                    raise ValueError(
                        f'"{size}" in file {fileName} is not a memory size.'
                    )
                # kernel uses KiB but names them kB, convert to Byte
                size = int(size[:-3]) * 1024
                logging.debug("Memory bank %s has size %s bytes.", memBank, size)
                return size
    raise ValueError(f"Failed to read total memory from {fileName}.")


def get_cpu_package_for_core(core):
    """Get the number of the physical package (socket) a core belongs to."""
    return int(
        util.read_file(
            f"/sys/devices/system/cpu/cpu{core}/topology/physical_package_id"
        )
    )


def get_cores_of_same_package_as(core):
    return util.parse_int_list(
        util.read_file(f"/sys/devices/system/cpu/cpu{core}/topology/core_siblings_list")
    )
