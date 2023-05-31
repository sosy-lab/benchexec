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

from benchexec import cgroups
from benchexec import util

sys.dont_write_bytecode = True  # prevent creation of .pyc files

__all__ = [
    "check_memory_size",
    "get_cpu_cores_per_run",
    "get_memory_banks_per_run",
    "get_cpu_package_for_core",
]


def get_cpu_cores_per_run(
    coreLimit,
    num_of_threads,
    use_hyperthreading,
    my_cgroups,
    coreSet=None,
    coreRequirement=None,
):
    """
    Sets variables and reads data from the machine to prepare for the distribution algorithm
    Preparation and the distribution algorithm itself are separated to facilitate
    testing the algorithm via Unittests

    The list of available cores is read from the cgroup file system,
    such that the assigned cores are a subset of the cores that the current process is allowed to use.
    Furthermore all currently supported topology data is read for each core and
    the cores are then organised accordingly into hierarchy_levels.
    hierarchy_levels is sorted so that the first dict maps hyper-threading siblings
    while the next dict in the list subsumes same or more cores per key (topology identifier)
    as the siblings dict but less than the following dict.
    Therefore when iterating through the list of dicts, each dict has less keys
    but the corresponding value is a list of greater length than the previous dict had.
    Thus hierarchy_levels reflects a hierarchy of the available topology layers from smallest to largest.
    Additionally, the list of available cores is converted into a list of VirtualCore objects
    that provide its ID and a list of the memory regions it belongs to.

    This script does currently not support situations where the available cores are
    asymmetrically split over CPUs, e.g. 3 cores on one CPU and 5 on another.

    @param coreLimit:           the number of cores for each thread
    @param num_of_threads:      the number of parallel benchmark executions
    @param use_hyperthreading:  boolean to check if no-hyperthreading method is being used
    @param coreSet:             the list of CPU core identifiers provided by a user,
                                None makes benchexec using all cores
    @return hierarchy_levels:   list of dicts of lists: each dict in the list corresponds to one topology layer
                                and maps from the identifier read from the topology to a list of the cores belonging to it
    """
    hierarchy_levels = []
    try:
        # read list of available CPU cores (int)
        allCpus_list = get_cpu_list(my_cgroups, coreSet)

        # read & prepare hyper-threading information, filter redundant entries
        siblings_of_core = get_siblings_mapping(allCpus_list)
        cleanList = []
        for core in siblings_of_core:
            if core not in cleanList:
                for sibling in siblings_of_core[core]:
                    if sibling != core:
                        cleanList.append(sibling)
        for element in cleanList:
            siblings_of_core.pop(element)
        # siblings_of_core will be added to hierarchy_levels list after sorting

        # read & prepare mapping of cores to L3 cache
        cores_of_L3cache = get_L3cache_mapping(allCpus_list)
        hierarchy_levels.append(cores_of_L3cache)

        # read & prepare mapping of cores to NUMA region
        cores_of_NUMA_Region = get_NUMA_mapping(allCpus_list)
        if cores_of_NUMA_Region:
            hierarchy_levels.append(cores_of_NUMA_Region)

        # read & prepare mapping of cores to group
        if cores_of_NUMA_Region:
            cores_of_group = get_group_mapping(cores_of_NUMA_Region)
            if cores_of_group:
                hierarchy_levels.append(cores_of_group)

        # read & prepare mapping of cores to physical package
        cores_of_package = get_package_mapping(allCpus_list)
        hierarchy_levels.append(cores_of_package)

        # read & prepare mapping of cores to die
        cores_of_die = get_die_mapping(allCpus_list)
        if cores_of_die:
            hierarchy_levels.append(cores_of_die)

        # read & prepare mapping of cores to cluster
        cores_of_cluster = get_cluster_mapping(allCpus_list)
        if cores_of_cluster:
            hierarchy_levels.append(cores_of_cluster)

        # read & prepare mapping of cores to drawer
        cores_of_drawer = get_drawer_mapping(allCpus_list)
        if cores_of_drawer:
            hierarchy_levels.append(cores_of_drawer)

        # read & prepare mapping of cores to book
        cores_of_book = get_book_mapping(allCpus_list)
        if cores_of_book:
            hierarchy_levels.append(cores_of_book)

    except ValueError as e:
        sys.exit(f"Could not read CPU information from kernel: {e}")

    def compare_hierarchy_by_dict_length(level):
        """comparator function for number of elements in a dict's value list"""
        return len(next(iter(level.values())))

    hierarchy_levels.sort(key=compare_hierarchy_by_dict_length, reverse=False)
    """sort hierarchy_levels (list of dicts) according to the dicts' value sizes"""

    # add siblings_of_core at the beginning of the list to ensure the correct index
    hierarchy_levels.insert(0, siblings_of_core)

    # create VirtualCores
    allCpus = {}
    """creates a dict of VirtualCore objects from core ID list"""
    for cpu_nr in allCpus_list:
        allCpus.update({cpu_nr: VirtualCore(cpu_nr, [])})

    for level in hierarchy_levels:  # hierarchy_levels (list of dicts)
        for key in level:
            for core in level[key]:
                allCpus[core].memory_regions.append(
                    key
                )  # memory_regions is a list of keys

    check_and_add_meta_level(hierarchy_levels, allCpus)
    return get_cpu_distribution(
        coreLimit,
        num_of_threads,
        use_hyperthreading,
        allCpus,
        siblings_of_core,
        hierarchy_levels,
        coreRequirement,
    )


def get_cpu_distribution(
    coreLimit,
    num_of_threads,
    use_hyperthreading,
    allCpus,
    siblings_of_core,
    hierarchy_levels,
    coreRequirement=None,
):
    """implements optional restrictions and calls the actual assignment function"""
    result = []

    # check if all HT siblings are available for benchexec
    all_cpus_set = set(allCpus.keys())
    for core, siblings in siblings_of_core.items():
        siblings_set = set(siblings)
        if not siblings_set.issubset(all_cpus_set):
            unusable_cores = siblings_set.difference(all_cpus_set)
            sys.exit(
                f"Core assignment is unsupported because siblings {unusable_cores} "
                f"of core {core} are not usable. "
                f"Please always make all virtual cores of a physical core available."
            )

    # no HT filter: delete all but the key core from siblings_of_core & hierarchy_levels
    if not use_hyperthreading:
        filter_hyperthreading_siblings(allCpus, siblings_of_core, hierarchy_levels)

    if not coreRequirement:
        result = core_allocation_algorithm(
            coreLimit,
            num_of_threads,
            use_hyperthreading,
            allCpus,
            siblings_of_core,
            hierarchy_levels,
        )
    else:
        if coreRequirement >= coreLimit:
            prelim_result = core_allocation_algorithm(
                coreRequirement,
                num_of_threads,
                use_hyperthreading,
                allCpus,
                siblings_of_core,
                hierarchy_levels,
            )
            for resultlist in prelim_result:
                result.append(resultlist[:coreLimit])
        else:
            i = coreLimit
            while i >= coreRequirement:
                if check_distribution_feasibility(
                    i,
                    num_of_threads,
                    use_hyperthreading,
                    allCpus,
                    siblings_of_core,
                    hierarchy_levels,
                    isTest=True,
                ):
                    break
                else:
                    i -= 1
            result = core_allocation_algorithm(
                i,
                num_of_threads,
                use_hyperthreading,
                allCpus,
                siblings_of_core,
                hierarchy_levels,
            )
    return result


class VirtualCore:
    """
    Generates an object for each available CPU core,
    providing its ID and a list of the memory regions it belongs to.
    @attr coreId: int returned from the system to identify a specific core
    @attr memory_regions: list with the ID of the corresponding regions the core belongs to sorted
                            according to its size
    """

    def __init__(self, coreId, memory_regions=None):
        self.coreId = coreId
        self.memory_regions = memory_regions

    def __str__(self):
        return str(self.coreId) + " " + str(self.memory_regions)


def filter_hyperthreading_siblings(allCpus, siblings_of_core, hierarchy_levels):
    """
    Deletes all but one hyperthreading sibling per physical core out of allCpus,
    siblings_of_core & hierarchy_levels
    @param allCpus: list of VirtualCore objects
    @param siblings_of_core:    mapping from one of the sibling cores to the list of siblings
                                including the core itself
    """
    for core in siblings_of_core:
        no_HT_filter = []
        for sibling in siblings_of_core[core]:
            if sibling != core:
                no_HT_filter.append(sibling)
        for virtual_core in no_HT_filter:
            siblings_of_core[core].remove(virtual_core)
            region_keys = allCpus[virtual_core].memory_regions
            i = 1
            while i < len(region_keys):
                hierarchy_levels[i][region_keys[i]].remove(virtual_core)
                i = i + 1
            allCpus.pop(virtual_core)


def check_distribution_feasibility(
    coreLimit,
    num_of_threads,
    use_hyperthreading,
    allCpus,
    siblings_of_core,
    hierarchy_levels,
    isTest=True,
):
    """Checks, whether the core distribution can work with the given parameters"""
    is_feasible = True

    # compare number of available cores to required cores per run
    coreCount = len(allCpus)
    if coreLimit > coreCount:
        if not isTest:
            sys.exit(
                f"Cannot run benchmarks with {coreLimit} CPU cores, "
                f"only {coreCount} CPU cores available."
            )
        else:
            is_feasible = False

    # compare number of available run to overall required cores
    if coreLimit * num_of_threads > coreCount:
        if not isTest:
            sys.exit(
                f"Cannot run {num_of_threads} benchmarks in parallel "
                f"with {coreLimit} CPU cores each, only {coreCount} CPU cores available. "
                f"Please reduce the number of threads to {coreCount // coreLimit}."
            )
        else:
            is_feasible = False

    coreLimit_rounded_up = calculate_coreLimit_rounded_up(siblings_of_core, coreLimit)
    chosen_level = calculate_chosen_level(hierarchy_levels, coreLimit_rounded_up)

    # calculate runs per unit of hierarchy level i
    unit_size = len(next(iter(hierarchy_levels[chosen_level].values())))
    assert unit_size >= coreLimit_rounded_up
    runs_per_unit = int(math.floor(unit_size / coreLimit_rounded_up))

    # compare num of units & runs per unit vs num_of_threads
    if len(hierarchy_levels[chosen_level]) * runs_per_unit < num_of_threads:
        if not isTest:
            sys.exit(
                f"Cannot assign required number of threads."
                f"Please reduce the number of threads to {len(hierarchy_levels[chosen_level]) * runs_per_unit}."
            )
        else:
            is_feasible = False

    # calculate if sub_units have to be split to accommodate the runs_per_unit
    sub_units_per_run = calculate_sub_units_per_run(
        coreLimit_rounded_up, hierarchy_levels, chosen_level
    )
    # number of nodes at subunit-Level / sub_units_per_run
    if len(hierarchy_levels[chosen_level - 1]) / sub_units_per_run < num_of_threads:
        if not isTest:
            sys.exit(
                f"Cannot split memory regions between runs. "
                f"Please reduce the number of threads to {math.floor(len(hierarchy_levels[chosen_level-1]) / sub_units_per_run)}."
            )
        else:
            is_feasible = False

    return is_feasible


def calculate_chosen_level(hierarchy_levels, coreLimit_rounded_up):
    """Calculates the hierarchy level necessary so that number of cores at the chosen_level is at least
    as big as the cores necessary for one thread"""
    chosen_level = 1
    # move up in hierarchy as long as the number of cores at the current level is smaller than the coreLimit
    # if the number of cores at the current level is as big as the coreLimit: exit loop
    while (
        chosen_level < len(hierarchy_levels) - 1
        and len(next(iter(hierarchy_levels[chosen_level].values())))
        < coreLimit_rounded_up
    ):
        chosen_level = chosen_level + 1
    return chosen_level


def calculate_coreLimit_rounded_up(siblings_of_core, coreLimit):
    """coreLimit_rounded_up (int): recalculate # cores for each run accounting for HT"""
    core_size = len(next(iter(siblings_of_core.values())))
    # Take value from hierarchy_levels instead from siblings_of_core
    coreLimit_rounded_up = int(math.ceil(coreLimit / core_size) * core_size)
    assert coreLimit <= coreLimit_rounded_up < (coreLimit + core_size)
    return coreLimit_rounded_up


def calculate_sub_units_per_run(coreLimit_rounded_up, hierarchy_levels, chosen_level):
    """calculate how many sub_units have to be used to accommodate the runs_per_unit"""
    sub_units_per_run = math.ceil(
        coreLimit_rounded_up / len(hierarchy_levels[chosen_level - 1][0])
    )
    return sub_units_per_run


def check_and_add_meta_level(hierarchy_levels, allCpus):
    """
    Adds a meta_level to hierarchy_levels to iterate through all cores (if necessary)
    """
    if len(hierarchy_levels[-1]) > 1:
        top_level_cores = []
        for node in hierarchy_levels[-1]:
            top_level_cores.extend(hierarchy_levels[-1][node])
        hierarchy_levels.append({0: top_level_cores})
        for cpu_nr in allCpus:
            allCpus[cpu_nr].memory_regions.append(0)


def get_sub_unit_dict(allCpus, parent_list, hLevel):
    child_dict = {}
    for element in parent_list:
        subSubUnitKey = allCpus[element].memory_regions[hLevel]
        if subSubUnitKey in list(child_dict.keys()):
            child_dict[subSubUnitKey].append(element)
        else:
            child_dict.update({subSubUnitKey: [element]})
    return child_dict


def core_allocation_algorithm(
    coreLimit,
    num_of_threads,
    use_hyperthreading,
    allCpus,
    siblings_of_core,
    hierarchy_levels,
):
    """Actual core distribution method:
    uses the architecture read from the file system by get_cpu_cores_per_run

    Calculates an assignment of the available CPU cores to a number
    of parallel benchmark executions such that each run gets its own cores
    without overlapping of cores between runs.
    In case the machine has hyper-threading, this method avoids
    putting two different runs on the same physical core.
    When assigning cores that belong to the same run, the method
    uses core that access the same memory regions, while distributing
    the parallel execution runs with as little shared memory as possible
    across all available CPUs.

    A few theoretically-possible cases are not supported,
    for example assigning three 10-core runs on a machine
    with two 16-core CPUs (this would have unfair core assignment
    and thus undesirable performance characteristics anyway).

    @param coreLimit:           the number of cores for each run
    @param num_of_threads:      the number of parallel benchmark executions
    @param use_hyperthreading:  boolean to check if no-hyperthreading method is being used
    @param allCpus:             list of all available core objects
    @param siblings_of_core:    mapping from one of the sibling cores to the list of siblings including the core itself
    @param hierarchy_levels:    list of dicts mapping from a memory region identifier to its belonging cores
    @return result:             list of lists each containing the cores assigned to the same thread
    """

    # check whether the distribution can work with the given parameters
    check_distribution_feasibility(
        coreLimit,
        num_of_threads,
        use_hyperthreading,
        allCpus,
        siblings_of_core,
        hierarchy_levels,
        isTest=False,
    )

    # check if all units of the same hierarchy level have the same number of cores
    for hierarchy_level in hierarchy_levels:
        if check_asymmetric_num_of_values(hierarchy_level):
            sys.exit(
                "Asymmetric machine architecture not supported: "
                "CPUs/memory regions with different number of cores."
            )

    # coreLimit_rounded_up (int): recalculate # cores for each run accounting for HT
    coreLimit_rounded_up = calculate_coreLimit_rounded_up(siblings_of_core, coreLimit)
    # Choose hierarchy level for core assignment
    chosen_level = calculate_chosen_level(hierarchy_levels, coreLimit_rounded_up)
    # calculate how many sub_units have to be used to accommodate the runs_per_unit
    sub_units_per_run = calculate_sub_units_per_run(
        coreLimit_rounded_up, hierarchy_levels, chosen_level
    )

    # Start core assignment algorithm
    result = []
    blocked_cores = []
    active_hierarchy_level = hierarchy_levels[chosen_level]
    while len(result) < num_of_threads:  # and i < len(active_hierarchy_level):
        """
        for each new thread, the algorithm searches the hierarchy_levels for a
        dict with an unequal number of cores, chooses the value list with the most cores and
        compiles a child dict with these cores, then again choosing the value list with the most cores ...
        until the value lists have the same length.
        Thus the algorithm finds the index i for hierarchy_levels that indicates the dict
        from which to continue the search for the cores with the highest distance from the cores
        assigned before
        """
        # choose cores for assignment:
        i = len(hierarchy_levels) - 1
        distribution_dict = hierarchy_levels[i]
        # start with highest dict: continue while length = 1 or equal length of values
        while i > 0:
            # if length of core lists equal:
            if check_symmetric_num_of_values(distribution_dict):
                i = i - 1
                distribution_dict = hierarchy_levels[i]
            else:
                # if length of core lists unequal: get element with highest length
                distribution_list = list(distribution_dict.values())
                distribution_list.sort(
                    key=lambda list_length: len(list_length), reverse=True
                )

                child_dict = get_sub_unit_dict(allCpus, distribution_list[0], i - 1)
                distribution_dict = child_dict.copy()
                if check_symmetric_num_of_values(child_dict):
                    break
                else:
                    i = i - 1
        """
        The values of the hierarchy_levels dict at index i are sorted by length and
        from the the largest list of values, the first core is used to identify
        the memory region and the list of cores relevant for the core assignment for the next thread
        """
        # return the memory region key of values first core at chosen_level
        spreading_memory_region_key = allCpus[
            list(distribution_dict.values())[0][0]
        ].memory_regions[chosen_level]
        # return the list of cores belonging to the spreading_memory_region_key
        active_cores = active_hierarchy_level[spreading_memory_region_key]

        # Core assignment per thread:
        cores = []
        for _sub_unit in range(sub_units_per_run):
            """
            the active cores at chosen level are assigned to the current thread
            ensuring the assignment of all cores belonging to the same key-value pair
            and all cores of one sub_unit before changing to the next sub_unit
            """
            # read key of sub_region from first element of active cores list
            key = allCpus[active_cores[0]].memory_regions[chosen_level - 1]

            # read list of cores of corresponding sub_region
            sub_unit_hierarchy_level = hierarchy_levels[chosen_level - 1]
            sub_unit_cores = sub_unit_hierarchy_level[key]

            while len(cores) < coreLimit and sub_unit_cores:
                """assigns the cores from sub_unit_cores list into child dict
                in accordance with their memory regions"""
                j = chosen_level - 1
                if j - 1 > 0:
                    j = j - 1

                child_dict = get_sub_unit_dict(allCpus, sub_unit_cores.copy(), j)
                """
                searches for the key-value pair that already provided cores for the assignment
                and therefore has the fewest elements in its value list while non-empty,
                and returns one of the cores in this key-value pair.
                If no cores have been assigned yet, any core can be chosen and the next best core is returned.
                """
                while j > 0:
                    if check_symmetric_num_of_values(child_dict):
                        break
                    else:
                        j -= 1
                        distribution_list = list(child_dict.values())
                        for iter2 in distribution_list.copy():
                            if len(iter2) == 0:
                                distribution_list.remove(iter2)
                        distribution_list.sort(reverse=False)
                        child_dict = get_sub_unit_dict(allCpus, distribution_list[0], j)
                next_core = list(child_dict.values())[0][0]

                """
                Adds the core selected before and its hyper-threading sibling to the thread
                and deletes those cores from all hierarchy_levels
                """
                core_with_siblings = hierarchy_levels[0][
                    allCpus[next_core].memory_regions[0]
                ].copy()
                for core in core_with_siblings:
                    if len(cores) < coreLimit:
                        cores.append(core)  # add core&siblings to results
                    else:
                        blocked_cores.append(
                            core
                        )  # add superfluous cores to blocked_cores
                    core_clean_up(core, allCpus, hierarchy_levels)

            while sub_unit_cores:
                core_clean_up(sub_unit_cores[0], allCpus, hierarchy_levels)
                # active_cores remove(sub_unit_cores[0])
                # sub_unit_cores remove(sub_unit_cores[0])

            # if coreLimit reached: append core to result, delete remaining cores from active_cores
            if len(cores) == coreLimit:
                result.append(cores)

    # cleanup: while-loop stops before running through all units: while some active_cores-lists
    # & sub_unit_cores-lists are empty, other stay half-full or full

    return result


def check_symmetric_num_of_values(hierarchy_level):
    """returns True if the number of values in the lists of the key-value pairs
    is equal throughout the dict"""
    return not check_asymmetric_num_of_values(hierarchy_level)


def check_asymmetric_num_of_values(hierarchy_level):
    """returns True if the number of values in the lists of the key-value pairs
    is not equal throughout the dict"""
    is_asymmetric = False
    cores_per_unit = len(next(iter(hierarchy_level.values())))
    if any(len(cores) != cores_per_unit for cores in hierarchy_level.values()):
        is_asymmetric = True
    return is_asymmetric


def core_clean_up(core, allCpus, hierarchy_levels):
    current_core_regions = allCpus[core].memory_regions
    for mem_index in range(len(current_core_regions)):
        region = current_core_regions[mem_index]
        hierarchy_levels[mem_index][region].remove(core)


# return list of available CPU cores
def get_cpu_list(my_cgroups, coreSet=None):
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
        allCpus_list = [core for core in allCpus if core in coreSet]
    allCpus_list = frequency_filter(allCpus, 0.05)
    logging.debug("List of available CPU cores is %s.", allCpus)
    return allCpus_list


def frequency_filter(allCpus_list, threshold):
    """
    Filters the list of all available CPU cores so that only the fastest cores
    are used for the benchmark run.
    Cores with a maximal frequency smaller than the distance of the defined threshold
    from the fastest core are removed from allCpus_list.

    @param allCpus_list: list of all cores available for the benchmark run
    @param threshold: accepted difference in the maximal frequency of a core from
    the fastest core to still be used in the benchmark run
    @return: filtered allCpus_list with only the fastest cores
    """
    cpu_max_frequencies = collections.defaultdict(list)
    for core in allCpus_list:
        max_freq = int(
            util.read_file(
                f"/sys/devices/system/cpu/cpu{core}/cpufreq/cpuinfo_max_freq"
            )
        )
        cpu_max_frequencies[max_freq].append(core)
    freq_threshold = max(cpu_max_frequencies.keys()) * (1 - threshold)
    for key in cpu_max_frequencies:
        if key < freq_threshold:
            for core in cpu_max_frequencies[key]:
                allCpus_list.remove(core)
    return allCpus_list


def get_siblings_mapping(allCpus):
    """Get hyperthreading siblings from core_cpus_list or thread_siblings_list (deprecated)."""
    siblings_of_core = {}
    # if no hyperthreading available, the siblings list contains only the core itself
    if util.try_read_file(
        f"/sys/devices/system/cpu/cpu{allCpus[0]}/topology/core_cpus_list"
    ):
        for core in allCpus:
            siblings = util.parse_int_list(
                util.read_file(
                    f"/sys/devices/system/cpu/cpu{core}/topology/core_cpus_list"
                )
            )
    elif util.try_read_file(
        f"/sys/devices/system/cpu/cpu{allCpus[0]}/topology/thread_siblings_list"
    ):
        for core in allCpus:
            siblings = util.parse_int_list(
                util.read_file(
                    f"/sys/devices/system/cpu/cpu{core}/topology/thread_siblings_list"
                )
            )
        siblings_of_core[core] = siblings
        logging.debug("Siblings of cores are %s.", siblings_of_core)
    else:
        raise ValueError("No siblings information accessible")
    return siblings_of_core


def get_die_id_for_core(core):
    """Get the id of the die a core belongs to."""
    return int(util.read_file(f"/sys/devices/system/cpu/cpu{core}/topology/die_id"))


def get_die_mapping(allCpus):
    """Generates a mapping from a die to its corresponding cores."""
    cores_of_die = collections.defaultdict(list)
    try:
        for core in allCpus:
            die = get_die_id_for_core(core)
            cores_of_die[die].append(core)
    except FileNotFoundError:
        cores_of_die = {}
        logging.warning(
            "Die information not available in /sys/devices/system/cpu/cpu{core}/topology/die_id"
        )
    logging.debug("Dies of cores are %s.", cores_of_die)
    return cores_of_die


def get_group_mapping(cores_of_NUMA_region):
    cores_of_groups = collections.defaultdict(list)
    nodes_of_groups = collections.defaultdict(list)
    # generates dict of all available nodes with their group nodes
    try:
        for node_id in cores_of_NUMA_region.keys():
            group = get_nodes_of_group(node_id)
            nodes_of_groups[node_id].extend(group)
    except FileNotFoundError:
        nodes_of_groups = {}
        logging.warning(
            "Information on node distances not available at /sys/devices/system/node/nodeX/distance"
        )
    # deletes superfluous entries after symmetry check
    clean_list = []
    for node_key in nodes_of_groups:
        if node_key not in clean_list:
            for node in nodes_of_groups[node_key]:
                if node != node_key:
                    if nodes_of_groups[node_key] == nodes_of_groups[node]:
                        clean_list.append(node)
                    else:
                        raise Exception("Non-conclusive system information")
    for element in clean_list:
        nodes_of_groups.pop(element)
    # sets new group id, replaces list of nodes with list of cores belonging to the nodes
    id_index = 0
    for node_list in nodes_of_groups.values():
        for entry in node_list:
            cores_of_groups[id_index].extend(cores_of_NUMA_region[entry])
        id_index += 1
    return cores_of_groups


def get_nodes_of_group(node_id):
    """
    returns the nodes that belong to the same group because they have a smaller distance
    between each other than to rest of the nodes
    """
    temp_list = (
        util.read_file(f"/sys/devices/system/node/node{node_id}/distance")
    ).split(" ")
    distance_list = []
    for split_string in temp_list:
        distance_list.append(int(split_string))
    group_list = get_closest_nodes(distance_list)
    return sorted(group_list)


def get_closest_nodes(distance_list):  # 10 11 11 11 20 20 20 20
    """returns a list of the indices of the node itself (smallest distance) and
    its next neighbours by distance
    The indices are the same as the node IDs"""
    sorted_distance_list = sorted(distance_list)
    smallest_distance = sorted_distance_list[0]
    for value in sorted_distance_list:
        if value != smallest_distance:
            second_to_smallest = value
            break
    group_list = []
    if distance_list.count(smallest_distance) == 1:
        group_list.append(distance_list.index(smallest_distance))
    else:
        raise Exception("More then one smallest distance")
    if distance_list.count(second_to_smallest) == 1:
        group_list.append(distance_list.index(second_to_smallest))
    elif distance_list.count(second_to_smallest) > 1:
        index = 0
        for dist in distance_list:
            if dist == second_to_smallest:
                group_list.append(index)
            index += 1
    return group_list  # [0 1 2 3]


def get_cluster_id_for_core(core):
    """Get the id of the cluster a core belongs to."""
    return int(util.read_file(f"/sys/devices/system/cpu/cpu{core}/topology/cluster_id"))


def get_cluster_mapping(allCpus):
    cores_of_cluster = collections.defaultdict(list)  # Zuordnung DIE ID zu core ID
    try:
        for core in allCpus:
            cluster = get_cluster_id_for_core(core)
            cores_of_cluster[cluster].append(core)
    except FileNotFoundError:
        cores_of_cluster = {}
        logging.debug(
            "No cluster information available at /sys/devices/system/cpu/cpuX/topology/"
        )
    logging.debug("Clusters of cores are %s.", cores_of_cluster)
    return cores_of_cluster


def get_book_id_for_core(core):
    """Get the id of the book a core belongs to."""
    return int(util.read_file(f"/sys/devices/system/cpu/cpu{core}/topology/book_id"))


def get_book_mapping(allCpus):
    cores_of_book = collections.defaultdict(list)
    try:
        for core in allCpus:
            book = get_book_id_for_core(core)
            cores_of_book[book].append(core)
    except FileNotFoundError:
        cores_of_book = {}
        logging.debug(
            "No book information available at /sys/devices/system/cpu/cpuX/topology/"
        )
    logging.debug("Books of cores are %s.", cores_of_book)
    return cores_of_book


def get_drawer_id_for_core(core):
    """Get the id of the drawer a core belongs to."""
    return int(util.read_file(f"/sys/devices/system/cpu/cpu{core}/topology/drawer_id"))


def get_drawer_mapping(allCpus):
    cores_of_drawer = collections.defaultdict(list)
    try:
        for core in allCpus:
            drawer = get_drawer_id_for_core(core)
            cores_of_drawer[drawer].append(core)
    except FileNotFoundError:
        cores_of_drawer = {}
        logging.debug(
            "No drawer information available at /sys/devices/system/cpu/cpuX/topology/"
        )
    logging.debug("drawers of cores are %s.", cores_of_drawer)
    return cores_of_drawer


def get_L3cache_id_for_core(core):
    """Check whether index level 3 is level 3 cache"""
    dir_path = f"/sys/devices/system/cpu/cpu{core}/cache/"
    index_L3_cache = ""
    for entry in os.listdir(dir_path):
        if entry.startswith("index"):
            if (
                int(
                    util.read_file(
                        f"/sys/devices/system/cpu/cpu{core}/cache/{entry}/level"
                    )
                )
                == 3
            ):
                index_L3_cache = entry
                break
    """Get the id of the Level 3 cache a core belongs to."""
    return int(
        util.read_file(f"/sys/devices/system/cpu/cpu{core}/cache/{index_L3_cache}/id")
    )


def get_L3cache_mapping(allCpus):
    cores_of_L3cache = collections.defaultdict(list)
    try:
        for core in allCpus:
            L3cache = get_L3cache_id_for_core(core)
            cores_of_L3cache[L3cache].append(core)
    except FileNotFoundError:
        cores_of_L3cache = {}
        logging.error(
            "Level 3 cache information not available at /sys/devices/system/cpu/cpuX/cache/cacheX"
        )
    logging.debug("Level 3 caches of cores are %s.", cores_of_L3cache)
    return cores_of_L3cache


# returns dict of mapping NUMA region to list of cores
def get_NUMA_mapping(allCpus):
    cores_of_NUMA_region = collections.defaultdict(list)
    for core in allCpus:
        coreDir = f"/sys/devices/system/cpu/cpu{core}/"
        NUMA_regions = _get_memory_banks_listed_in_dir(coreDir)
        if NUMA_regions:
            cores_of_NUMA_region[NUMA_regions[0]].append(core)
            # adds core to value list at key [NUMA_region[0]]
        else:
            # If some cores do not have NUMA information, skip using it completely
            logging.warning(
                "Kernel does not have NUMA support. Use benchexec at your own risk."
            )
            cores_of_NUMA_region = {}
            break
    logging.debug("Memory regions of cores are %s.", cores_of_NUMA_region)
    return cores_of_NUMA_region


# returns dict of mapping CPU/physical package to list of cores
def get_package_mapping(allCpus):
    cores_of_package = collections.defaultdict(list)
    for core in allCpus:
        package = get_cpu_package_for_core(core)
        cores_of_package[package].append(core)
    logging.debug("Physical packages of cores are %s.", cores_of_package)
    return cores_of_package


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

        if cgroups.MEMORY in my_cgroups:
            # We use the entries hierarchical_*_limit in memory.stat and not memory.*limit_in_bytes
            # because the former may be lower if memory.use_hierarchy is enabled.
            for key, value in my_cgroups.get_key_value_pairs(cgroups.MEMORY, "stat"):
                if (
                    key == "hierarchical_memory_limit"
                    or key == "hierarchical_memsw_limit"
                ):
                    check_limit(int(value))

        # Get list of all memory banks, either from memory assignment or from system.
        if not memoryAssignment:
            if cgroups.CPUSET in my_cgroups:
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
