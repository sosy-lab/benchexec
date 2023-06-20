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
from typing import Optional, List, Dict

from benchexec import cgroups
from benchexec import util

sys.dont_write_bytecode = True  # prevent creation of .pyc files

__all__ = [
    "check_memory_size",
    "get_cpu_cores_per_run",
    "get_memory_banks_per_run",
    "get_cpu_package_for_core",
]

# typing defintions
_2DIntList = List[List[int]]
HierarchyLevel = Dict[int, List[int]]


def get_cpu_cores_per_run(
    coreLimit: int,
    num_of_threads: int,
    use_hyperthreading: bool,
    my_cgroups,
    coreSet: Optional[List] = None,
    coreRequirement: Optional[int] = None,
) -> List[List[int]]:
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

    @param: coreLimit           the number of cores for each thread
    @param: num_of_threads      the number of parallel benchmark executions
    @param: use_hyperthreading  boolean to check if no-hyperthreading method is being used
    @param: coreSet             the list of CPU core identifiers provided by a user,None makes benchexec using all cores
    @return:                    list of lists, where each inner list contains the cores for one run
    """

    if (
        type(coreLimit) != int
        or type(num_of_threads) != int
        or type(use_hyperthreading) != bool
    ):
        sys.exit("Incorrect data type entered")

    if coreLimit < 1 or num_of_threads < 1:
        sys.exit("Only integers > 0 accepted for coreLimit & num_of_threads")

    hierarchy_levels = []
    try:
        # read list of available CPU cores (int)
        allowedCpus = get_cpu_list(my_cgroups)
        allCpus_list = get_cpu_list(my_cgroups, coreSet)
        logging.debug(allCpus_list)

        # read & prepare hyper-threading information, filter redundant entries
        siblings_of_core = get_siblings_mapping(allCpus_list)
        cleanList = []
        unused_siblings = []
        for core in siblings_of_core:
            if core not in cleanList:
                for sibling in siblings_of_core[core].copy():
                    if sibling != core:
                        cleanList.append(sibling)
                        if coreSet:
                            if sibling not in coreSet:
                                unused_siblings.append(sibling)
                                siblings_of_core[core].remove(sibling)
        for element in cleanList:
            if element in siblings_of_core:
                siblings_of_core.pop(element)
        # siblings_of_core will be added to hierarchy_levels list after sorting

        levels_to_add = [
            get_L3cache_mapping(allCpus_list),
            get_package_mapping(allCpus_list),
            get_die_mapping(allCpus_list),
            get_cluster_mapping(allCpus_list),
            get_drawer_mapping(allCpus_list),
            get_book_mapping(allCpus_list),
        ]
        for mapping in levels_to_add:
            if mapping:
                hierarchy_levels.append(mapping)

        # read & prepare mapping of cores to NUMA region
        cores_of_NUMA_Region = get_NUMA_mapping(allCpus_list)
        if cores_of_NUMA_Region:
            hierarchy_levels.append(cores_of_NUMA_Region)

        # read & prepare mapping of cores to group
        if cores_of_NUMA_Region:
            cores_of_group = get_group_mapping(cores_of_NUMA_Region)
            if cores_of_group:
                hierarchy_levels.append(cores_of_group)

    except ValueError as e:
        sys.exit(f"Could not read CPU information from kernel: {e}")

    # check if all HT siblings are available for benchexec
    all_cpus_set = set(allCpus_list)
    unusable_cores = []
    for core, siblings in siblings_of_core.items():
        siblings_set = set(siblings)
        if not siblings_set.issubset(all_cpus_set):
            unusable_cores.extend(list(siblings_set.difference(all_cpus_set)))

    unusable_cores_set = set(unusable_cores)
    unavailable_cores = unusable_cores_set.difference(set(allowedCpus))
    if len(unavailable_cores) > 0:
        sys.exit(
            f"Core assignment is unsupported because siblings {unavailable_cores} "
            f"are not usable. "
            f"Please always make all virtual cores of a physical core available."
        )

    def compare_hierarchy_by_dict_length(level: HierarchyLevel):
        """comparator function for number of elements in a dict's value list"""
        return len(next(iter(level.values())))

    hierarchy_levels.sort(key=compare_hierarchy_by_dict_length, reverse=False)
    """sort hierarchy_levels (list of dicts) according to the dicts' value sizes"""

    # add siblings_of_core at the beginning of the list to ensure the correct index
    hierarchy_levels.insert(0, siblings_of_core)

    hierarchy_levels = filter_duplicate_hierarchy_levels(hierarchy_levels)

    logging.debug(hierarchy_levels)

    # creates a dict of VirtualCore objects from core ID list
    allCpus = {}
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


def filter_duplicate_hierarchy_levels(
    hierarchy_levels: List[HierarchyLevel],
) -> List[HierarchyLevel]:
    """
    Checks hierarchy levels for duplicates in the values of each dict key and return a filtered version of it

    @param: hierarchy_levels    the list of hierarchyLevels to be filtered for duplicate levels
    @return:                    a list of hierarchyLevels without identical levels
    """
    removeList = []
    filteredList = hierarchy_levels.copy()
    for index in range(len(hierarchy_levels) - 1):
        if len(hierarchy_levels[index]) == len(hierarchy_levels[index + 1]):
            allIdentical = True
            for key in hierarchy_levels[index]:
                set1 = set(hierarchy_levels[index][key])
                anyIdentical = False
                if any(
                    set1 == (set(s2)) for s2 in hierarchy_levels[index + 1].values()
                ):
                    anyIdentical = True
                allIdentical = allIdentical and anyIdentical
            if allIdentical:
                removeList.append(hierarchy_levels[index + 1])
    for level in removeList:
        filteredList.remove(level)
    return filteredList


class VirtualCore:
    """
    Generates an object for each available CPU core,
    providing its ID and a list of the memory regions it belongs to.
    @attr coreId: int returned from the system to identify a specific core
    @attr memory_regions: list with the ID of the corresponding regions the core belongs to sorted
    according to its size
    """

    def __init__(self, coreId: int, memory_regions: List[int]):
        self.coreId = coreId
        self.memory_regions = memory_regions

    def __str__(self):
        return str(self.coreId) + " " + str(self.memory_regions)


def get_cpu_distribution(
    coreLimit: int,
    num_of_threads: int,
    use_hyperthreading: bool,
    allCpus: Dict[int, VirtualCore],
    siblings_of_core: HierarchyLevel,
    hierarchy_levels: List[HierarchyLevel],
    coreRequirement: Optional[int] = None,
) -> List[List[int]]:
    """
    Implements optional restrictions and calls the actual assignment function

    @param: coreLimit           the number of cores for each parallel benchmark execution
    @param: num_of_threads      the number of parallel benchmark executions
    @param: use_hyperthreading  boolean to check if no-hyperthreading method is being used
    @param: allCpus             list of @VirtualCore Objects to address a core from its id to the ids of the memory regions
    @param: siblings_of_core    mapping from one of the sibling cores to the list of siblings including the core itself
    @param: hierarchy_levels    list of dicts of lists: each dict in the list corresponds to one topology layer and maps from the identifier read from the topology to a list of the cores belonging to it
    @param: coreRequirement     minimum number of cores to be reserved for each execution run
    @return:                    list of lists, where each inner list contains the cores for one run
    """
    result = []

    # no HT filter: delete all but the key core from siblings_of_core & hierarchy_levels
    if not use_hyperthreading:
        filter_hyperthreading_siblings(allCpus, siblings_of_core, hierarchy_levels)

    if not coreRequirement:
        result = core_allocation_algorithm(
            coreLimit,
            num_of_threads,
            allCpus,
            siblings_of_core,
            hierarchy_levels,
        )
    else:
        if coreRequirement >= coreLimit:
            # reserves coreRequirement number of cores of which coreLimit is used
            prelim_result = core_allocation_algorithm(
                coreRequirement,
                num_of_threads,
                allCpus,
                siblings_of_core,
                hierarchy_levels,
            )
            for resultlist in prelim_result:
                result.append(resultlist[:coreLimit])
        else:
            i = coreLimit
            while i >= coreRequirement:
                # uses as many cores as possible (with maximum coreLimit), but at least coreRequirement num of cores
                if check_distribution_feasibility(
                    i,
                    num_of_threads,
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
                allCpus,
                siblings_of_core,
                hierarchy_levels,
            )
    return result


def filter_hyperthreading_siblings(
    allCpus: Dict[int, VirtualCore],
    siblings_of_core: HierarchyLevel,
    hierarchy_levels: List[HierarchyLevel],
) -> None:
    """
    Deletes all but one hyperthreading sibling per physical core out of allCpus,
    siblings_of_core & hierarchy_levels
    @param: allCpus             list of VirtualCore objects
    @param: siblings_of_core    mapping from one of the sibling cores to the list of siblings
                                including the core itself
    @param: hierarchy_levels    list of dicts of lists: each dict in the list corresponds to one topology layer and maps from the identifier read from the topology to a list of the cores belonging to it
    """
    for core in siblings_of_core:
        no_HT_filter = []
        for sibling in siblings_of_core[core]:
            if sibling != core:
                no_HT_filter.append(sibling)
        for virtual_core in no_HT_filter:
            siblings_of_core[core].remove(virtual_core)
            region_keys = allCpus[virtual_core].memory_regions
            i = 0
            while i < len(region_keys):
                if virtual_core in hierarchy_levels[i][region_keys[i]]:
                    hierarchy_levels[i][region_keys[i]].remove(virtual_core)
                i = i + 1
            allCpus.pop(virtual_core)


def check_distribution_feasibility(
    coreLimit: int,
    num_of_threads: int,
    allCpus: Dict[int, VirtualCore],
    siblings_of_core: HierarchyLevel,
    hierarchy_levels: List[HierarchyLevel],
    isTest: bool = True,
) -> bool:
    """
    Checks, whether the core distribution can work with the given parameters

    @param: coreLimit           the number of cores for each parallel benchmark execution
    @param: num_of_threads      the number of parallel benchmark executions
    @param: allCpus             list of @VirtualCore Objects to address a core from its id to the ids of the memory regions
    @param: siblings_of_core    mapping from one of the sibling cores to the list of siblings including the core itself
    @param: hierarchy_levels    list of dicts of lists: each dict in the list corresponds to one topology layer and maps from the identifier read from the topology to a list of the cores belonging to it
    @param: isTest              boolean whether the check is used to test the coreLimit or for the actual core allocation
    @return:                    list of lists, where each inner list contains the cores for one run
    """
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
            num_of_possible_runs = len(hierarchy_levels[chosen_level]) * runs_per_unit
            sys.exit(
                f"Cannot assign required number of threads."
                f"Please reduce the number of threads to {num_of_possible_runs}."
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
            max_desirable_runs = math.floor(
                len(hierarchy_levels[chosen_level - 1]) / sub_units_per_run
            )
            sys.exit(
                f"Cannot split memory regions between runs. "
                f"Please reduce the number of threads to {max_desirable_runs}."
            )
        else:
            is_feasible = False

    return is_feasible


def calculate_chosen_level(
    hierarchy_levels: List[HierarchyLevel], coreLimit_rounded_up: int
) -> int:
    """
    Calculates the hierarchy level necessary so that number of cores at the chosen_level is at least
    as big as the cores necessary for one thread

    @param: hierarchy_levels        list of dicts of lists: each dict in the list corresponds to one topology layer and
                                    maps from the identifier read from the topology to a list of the cores belonging to it
    @param: coreLimit_rounded_up    rounding up the coreLimit to a multiple of the num of hyper-threading siblings per core
    @return:                        calculated chosen level as index
    """

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


def calculate_coreLimit_rounded_up(
    siblings_of_core: HierarchyLevel, coreLimit: int
) -> int:
    """
    coreLimit_rounded_up (int): recalculate # cores for each run accounting for HT

    @param: hierarchy_levels    list of dicts of lists: each dict in the list corresponds to one topology layer and
                                maps from the identifier read from the topology to a list of the cores belonging to it
    @param: coreLimit           the number of cores for each parallel benchmark execution
    @return:                    rounding up the coreLimit to a multiple of the num of hyper-threading siblings per core
    """
    core_size = len(next(iter(siblings_of_core.values())))
    # Take value from hierarchy_levels instead from siblings_of_core
    coreLimit_rounded_up = int(math.ceil(coreLimit / core_size) * core_size)
    assert coreLimit <= coreLimit_rounded_up < (coreLimit + core_size)
    return coreLimit_rounded_up


def calculate_sub_units_per_run(
    coreLimit_rounded_up: int,
    hierarchy_levels: List[HierarchyLevel],
    chosen_level: int,
) -> int:
    """
    calculate how many sub_units (units on the hierarchy level below chosen level) have to be used to accommodate the coreLimit_rounded_up

    @param: coreLimit_rounded_up    rounding up the coreLimit to a multiple of the num of hyper-threading siblings per core
    @param: hierarchy_levels        list of dicts of lists: each dict in the list corresponds to one topology layer and
                                    maps from the identifier read from the topology to a list of the cores belonging to it
    @return:                        number of subunits (rounded up) to accommodate the coreLimit
    """
    sub_units_per_run = math.ceil(
        coreLimit_rounded_up / len(hierarchy_levels[chosen_level - 1][0])
    )
    return sub_units_per_run


def check_and_add_meta_level(
    hierarchy_levels: List[HierarchyLevel], allCpus: Dict[int, VirtualCore]
) -> None:
    """
    Adds a meta_level or root_level which includes all cores to hierarchy_levels (if necessary).
    This is necessary to iterate through all cores if the highest hierarchy level consists of more than one unit.
    Also adds the identifier for the new level to the memory region of all cores in allCpus
    @param: hierarchy_levels    list of dicts of lists: each dict in the list corresponds to one topology layer and
                                maps from the identifier read from the topology to a list of the cores belonging to it
    @param: allCpus             list of @VirtualCore Objects to address a core from its id to the ids of the memory regions
    """
    if len(hierarchy_levels[-1]) > 1:
        top_level_cores = []
        for node in hierarchy_levels[-1]:
            top_level_cores.extend(hierarchy_levels[-1][node])
        hierarchy_levels.append({0: top_level_cores})
        for cpu_nr in allCpus:
            allCpus[cpu_nr].memory_regions.append(0)


def get_sub_unit_dict(
    allCpus: Dict[int, VirtualCore], parent_list: List[int], hLevel: int
) -> Dict[int, List[int]]:
    """
    Generates a dict including all units at a specify hierarchy level which consist of cores from parent_list
    Collects all region keys from the hierarchy level where the core ids in parent_list are stored and returns
    the collected data as dictionary

    @param: allCpus       list of @VirtualCore Objects to address a core from its id to the ids of the memory regions
    @param: parent_list   list of core ids from the parent hierarchyLevel
    @param: hLevel        the index of the hierarchy level to search in
    """

    child_dict = collections.defaultdict(list)
    for element in parent_list:
        subSubUnitKey = allCpus[element].memory_regions[hLevel]
        child_dict[subSubUnitKey].append(element)
    return child_dict


def core_allocation_algorithm(
    coreLimit: int,
    num_of_threads: int,
    allCpus: Dict[int, VirtualCore],
    siblings_of_core: HierarchyLevel,
    hierarchy_levels: List[HierarchyLevel],
) -> List[List[int]]:
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

    @param: coreLimit           the number of cores for each parallel execution run
    @param: num_of_threads      the number of parallel benchmark executions
    @param: use_hyperthreading  boolean to check if no-hyperthreading method is being used
    @param: allCpus             list of all available core objects
    @param: siblings_of_core    mapping from one of the sibling cores to the list of siblings including the core itself
    @param: hierarchy_levels    list of dicts mapping from a memory region identifier to its belonging cores
    @return result:             list of lists each containing the cores assigned to the same thread
    """

    # check whether the distribution can work with the given parameters
    check_distribution_feasibility(
        coreLimit,
        num_of_threads,
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
                    if i > chosen_level:
                        while i >= chosen_level and i > 0:
                            i = i - 1
                            # if length of core lists unequal: get element with highest length
                            distribution_list = list(distribution_dict.values())
                            distribution_list.sort(
                                key=lambda list_length: len(list_length), reverse=True
                            )

                            child_dict = get_sub_unit_dict(
                                allCpus, distribution_list[0], i - 1
                            )
                            distribution_dict = child_dict.copy()
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
                # active_cores & sub_unit_cores are deleted as well since they're just pointers
                # to hierarchy_levels

            # if coreLimit reached: append core to result, delete remaining cores from active_cores
            if len(cores) == coreLimit:
                result.append(cores)

    # cleanup: while-loop stops before running through all units: while some active_cores-lists
    # & sub_unit_cores-lists are empty, other stay half-full or full
    logging.debug(f"Core allocation:{result}")
    return result


def check_symmetric_num_of_values(hierarchy_level: HierarchyLevel) -> bool:
    """
    returns True if the number of values in the lists of the key-value pairs
    is equal throughout the dict

    @param: hierarchy_levels    list of dicts of lists: each dict in the list corresponds to one topology layer and
                                maps from the identifier read from the topology to a list of the cores belonging to it
    @return:                    true if symmetric
    """
    return not check_asymmetric_num_of_values(hierarchy_level)


def check_asymmetric_num_of_values(hierarchy_level: HierarchyLevel) -> bool:
    """
    returns True if the number of values in the lists of the key-value pairs
    is not equal throughout the dict

    @param: hierarchy_levels    list of dicts of lists: each dict in the list corresponds to one topology layer and
                                maps from the identifier read from the topology to a list of the cores belonging to it
    @return:                    true if asymmetric
    """
    is_asymmetric = False
    cores_per_unit = len(next(iter(hierarchy_level.values())))
    if any(len(cores) != cores_per_unit for cores in hierarchy_level.values()):
        is_asymmetric = True
    return is_asymmetric


def core_clean_up(
    core: int,
    allCpus: Dict[int, VirtualCore],
    hierarchy_levels: List[HierarchyLevel],
) -> None:
    """
    Delete the given core Id from all hierarchy levels and remove unit if empty

    @param: core                Id of the core to delete
    @param: allCpus             list of all available core objects
    @param: hierarchy_levels    list of dicts of lists: each dict in the list corresponds to one topology layer and
                                maps from the identifier read from the topology to a list of the cores belonging to it
    """
    current_core_regions = allCpus[core].memory_regions
    for mem_index in range(len(current_core_regions)):
        region = current_core_regions[mem_index]
        hierarchy_levels[mem_index][region].remove(core)
        if len(hierarchy_levels[mem_index][region]) == 0:
            hierarchy_levels[mem_index].pop(region)


def get_cpu_list(my_cgroups, coreSet: Optional[List] = None) -> List[int]:
    """
    retrieves all cores available to the users cgroup.
    If a coreSet is provided, the list of all available cores is reduced to those cores
    that are in both - available cores and coreSet.
    A filter is applied to make sure, all cores used for the benchmark run
    at the same clock speed (allowing a deviation of 0.05 (5%) from the highest frequency)
    @param cgroup
    @param coreSet list of cores to be used in the assignment as specified by the user
    @return list of available cores
    """
    # read list of available CPU cores
    allCpus = my_cgroups.read_allowed_cpus()

    # Filter CPU cores according to the list of identifiers provided by a user
    if coreSet:
        invalid_cores = sorted(set(coreSet).difference(set(allCpus)))
        if invalid_cores:
            raise ValueError(
                "The following provided CPU cores are not available: "
                + ", ".join(map(str, invalid_cores))
            )
        allCpus_list = [core for core in allCpus if core in coreSet]
        allCpus_list = frequency_filter(allCpus_list, 0.05)
    else:
        allCpus_list = frequency_filter(allCpus, 0.05)
    logging.debug("List of available CPU cores is %s.", allCpus_list)
    return allCpus_list


def frequency_filter(allCpus_list: List[int], threshold: float) -> List[int]:
    """
    Filters the list of all available CPU cores so that only the fastest cores
    are used for the benchmark run.
    Only cores with a maximal frequency within the distance of the defined threshold
    from the maximal frequency of the fastest core are added to the filtered_allCpus_list
    and returned for further use. (max_frequency of core) >= (1-threshold)*(max_frequency of fastest core)
    All cores that are slower will not be used for the benchmark and displayed in a debug message.

    @param: allCpus_list    list of all cores available for the benchmark run
    @param: threshold       accepted difference (as percentage) in the maximal frequency of a core from
                            the fastest core to still be used in the benchmark run
    @return:                filtered_allCpus_list with only the fastest cores
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
    filtered_allCpus_list = []
    slow_cores = []
    for key in cpu_max_frequencies:
        if key >= freq_threshold:
            filtered_allCpus_list.extend(cpu_max_frequencies[key])
        else:
            slow_cores.extend(cpu_max_frequencies[key])
    fastest = max(cpu_max_frequencies.keys())
    if slow_cores:
        logging.debug(
            f"Unused cores due to frequency more than {threshold*100}% below frequency of fastest core ({fastest}): {slow_cores}"
        )
    return filtered_allCpus_list


def get_generic_mapping(
    allCpus_list: List[int], mappingPath: str, mappingName: str = "generic"
) -> HierarchyLevel:
    """
    Generic mapping function for multiple layers that can be read the same way. Read data from given path
    for each cpu id listed in allCpus_list.

    @param: allCpus_list    list of cpu Ids to be read
    @param: mappingPath     system path where to read from
    @param: mappingName     name of the mapping to be read
    @return:                mapping of unit id to list of cores (dict)
    """

    cores_of_generic = collections.defaultdict(list)
    try:
        for core in allCpus_list:
            generic_level = int(util.read_file(mappingPath.format(str(core))))
            cores_of_generic[generic_level].append(core)
    except FileNotFoundError:
        logging.debug(f"{mappingName} information not available at {mappingPath}")
        return {}
    logging.debug(f"{mappingName} of cores are %s.", cores_of_generic)
    return cores_of_generic


def get_siblings_mapping(allCpus_list: List[int]) -> HierarchyLevel:
    """
    Get hyperthreading siblings from core_cpus_list or thread_siblings_list (deprecated).

    @param: allCpus_list    list of cpu Ids to be read
    @return:                mapping of siblings id to list of cores (dict)
    """
    siblings_of_core = {}
    path = "/sys/devices/system/cpu/cpu{}/topology/{}"
    usePath = ""
    # if no hyperthreading available, the siblings list contains only the core itself
    if os.path.isfile(path.format(str(allCpus_list[0]), "core_cpus_list")):
        usePath = "core_cpus_list"
    elif os.path.isfile(path.format(str(allCpus_list[0]), "thread_siblings_list")):
        usePath = "thread_siblings_list"
    else:
        raise ValueError("No siblings information accessible")

    for core in allCpus_list:
        siblings = util.parse_int_list(util.read_file(path.format(str(core), usePath)))
        siblings_of_core[core] = siblings

    logging.debug("Siblings of cores are %s.", siblings_of_core)
    return siblings_of_core


def get_die_mapping(allCpus_list: List[int]) -> HierarchyLevel:
    """
    Generates a mapping from a die to its corresponding cores.

    @param: allCpus_list    list of cpu Ids to be read
    @return:                mapping of die id to list of cores (dict)
    """
    return get_generic_mapping(
        allCpus_list, "/sys/devices/system/cpu/cpu{}/topology/die_id", "Dies"
    )


def get_group_mapping(cores_of_NUMA_region: HierarchyLevel) -> HierarchyLevel:
    """
    Generates a mapping from groups to their corresponding cores.

    @param: allCpus_list    list of cpu Ids to be read
    @return:                mapping of group id to list of cores (dict)
    """

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
    logging.debug("nodes_of_groups: %s", nodes_of_groups)
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
    logging.debug("Groups of cores are %s.", cores_of_groups)
    return cores_of_groups


def get_nodes_of_group(node_id: int) -> List[int]:
    """
    returns the nodes that belong to the same group because they have a smaller distance
    between each other than to rest of the nodes

    @param: node_id
    @return:list of nodes of the group that the node_id belongs to
    """
    temp_list = (
        util.read_file(f"/sys/devices/system/node/node{node_id}/distance")
    ).split(" ")
    distance_list = []
    for split_string in temp_list:
        distance_list.append(int(split_string))
    group_list = get_closest_nodes(distance_list)
    return sorted(group_list)


def get_closest_nodes(distance_list: List[int]) -> List[int]:  # 10 11 11 11 20 20 20 20
    """
    This function groups nodes according to their distance from each other.

    @param: list of distances of all nodes from the node that the list is retrieved from
    @return: list of the indices of the node itself (smallest distance) and its next neighbours by distance.

    We assume that the distance to other nodes is smaller than the distance of the core to itself.

    The indices are the same as the node IDs. That means that in a list [10 11 20 20],
    the distance from node0 to node0 is 10, the distance from node0 to node1 (index1 of the list) is 11,
    and the distance from node0 to node2 and node3 is both 20.

    If there are only 2 different distances available, they are assigned into different groups.
    """
    sorted_distance_list = sorted(distance_list)
    smallest_distance = sorted_distance_list[0]
    greatest_distance = sorted_distance_list[-1]
    for value in sorted_distance_list:
        if value != smallest_distance:
            second_to_smallest = value
            break
    group_list = []
    if distance_list.count(smallest_distance) == 1:
        group_list.append(distance_list.index(smallest_distance))
    else:
        # we assume that all other nodes are slower to access than the core itself
        raise Exception("More then one smallest distance")
    if second_to_smallest != greatest_distance:
        index = 0
        for dist in distance_list:
            if dist == second_to_smallest:
                group_list.append(index)
            index += 1
    return group_list  # [0 1 2 3]


def get_cluster_mapping(allCpus_list: List[int]) -> HierarchyLevel:
    """
    Generates a mapping from a cluster to its corresponding cores.

    @param: allCpus_list    list of cpu Ids to be read
    @return:                mapping of cluster id to list of cores (dict)
    """

    return get_generic_mapping(
        allCpus_list, "/sys/devices/system/cpu/cpu{}/topology/cluster_id", "Clusters"
    )


def get_book_mapping(allCpus_list: List[int]) -> HierarchyLevel:
    """
    Generates a mapping from a book to its corresponding cores.

    @param: allCpus_list    list of cpu Ids to be read
    @return:                mapping of book id to list of cores (dict)
    """
    return get_generic_mapping(
        allCpus_list, "/sys/devices/system/cpu/cpu{}/topology/book_id", "Books"
    )


def get_drawer_mapping(allCpus_list: List[int]) -> HierarchyLevel:
    """
    Generates a mapping from a drawer to its corresponding cores.

    @param: allCpus_list    list of cpu Ids to be read
    @return:                mapping of drawer id to list of cores (dict)
    """
    return get_generic_mapping(
        allCpus_list, "/sys/devices/system/cpu/cpu{}/topology/drawer_id", "drawers"
    )


def get_L3cache_id_for_core(core: int) -> int:
    """
    Check whether index level 3 is level 3 cache and returns id of L3 cache

    @param: core    id of the core whose L3cache id is retreived
    @return:        identifier (int) for the L3 cache the core belongs to
    """
    dir_path = f"/sys/devices/system/cpu/cpu{core}/cache/"
    index_L3_cache = ""
    for entry in os.listdir(dir_path):
        if entry.startswith("index"):
            cacheIndex = int(
                util.read_file(f"/sys/devices/system/cpu/cpu{core}/cache/{entry}/level")
            )
            if cacheIndex == 3:
                index_L3_cache = entry
                break
    """Get the id of the Level 3 cache a core belongs to."""
    return int(
        util.read_file(f"/sys/devices/system/cpu/cpu{core}/cache/{index_L3_cache}/id")
    )


def get_L3cache_mapping(allCpus_list: List[int]) -> HierarchyLevel:
    """
    Generates a mapping from a L3 Cache to its corresponding cores.

    @param: allCpus_list    list of cpu Ids to be read
    @return:                mapping of L3 Cache id to list of cores (dict)
    """
    cores_of_L3cache = collections.defaultdict(list)
    try:
        for core in allCpus_list:
            L3cache = get_L3cache_id_for_core(core)
            cores_of_L3cache[L3cache].append(core)
    except FileNotFoundError:
        cores_of_L3cache = {}
        logging.debug(
            "Level 3 cache information not available at /sys/devices/system/cpu/cpuX/cache/cacheX"
        )
    logging.debug("Level 3 caches of cores are %s.", cores_of_L3cache)
    return cores_of_L3cache


def get_NUMA_mapping(allCpus_list: List[int]) -> HierarchyLevel:
    """
    Generates a mapping from a Numa Region to its corresponding cores.

    @param: allCpus_list    list of cpu Ids to be read
    @return:                mapping of Numa Region id to list of cores (dict)
    """
    cores_of_NUMA_region = collections.defaultdict(list)
    for core in allCpus_list:
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
            return {}
    logging.debug("Memory regions of cores are %s.", cores_of_NUMA_region)
    return cores_of_NUMA_region


def get_package_mapping(allCpus_list: List[int]) -> HierarchyLevel:
    """
    Generates a mapping from a CPU/physical package to its corresponding cores.

    @param: allCpus_list    list of cpu Ids to be read
    @return:                mapping of CPU/physical package id to list of cores (dict)
    """
    return get_generic_mapping(
        allCpus_list,
        "/sys/devices/system/cpu/cpu{}/topology/physical_package_id",
        "Physical packages",
    )


def get_memory_banks_per_run(coreAssignment, cgroups) -> Optional[_2DIntList]:
    """
    Get an assignment of memory banks to runs that fits to the given coreAssignment,
    i.e., no run is allowed to use memory that is not local (on the same NUMA node)
    to one of its CPU cores.
    """
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


def _get_memory_banks_listed_in_dir(path) -> List[int]:
    """
    Get all memory banks the kernel lists in a given directory.
    Such a directory can be /sys/devices/system/node/ (contains all memory banks)
    or /sys/devices/system/cpu/cpu*/ (contains all memory banks on the same NUMA node as that core).
    """
    # Such directories contain entries named "node<id>" for each memory bank
    return [int(entry[4:]) for entry in os.listdir(path) if entry.startswith("node")]


def check_memory_size(memLimit, num_of_threads, memoryAssignment, my_cgroups):
    """
    Check whether the desired amount of parallel benchmarks fits in the memory.
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
    """
    Get the size of a memory bank in bytes.
    """
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


def get_cpu_package_for_core(core: int) -> int:
    """
    Get the number of the physical package (socket) a core belongs to.

    @attention:     This function is exported and therefore not obsolet yet (l.25)
    @param: core    id of core
    @return:        identifier of the physical package the core belongs to
    """
    return int(
        util.read_file(
            f"/sys/devices/system/cpu/cpu{core}/topology/physical_package_id"
        )
    )


def get_cores_of_same_package_as(core: int) -> List[int]:
    """
    Generates a list of all cores that belong to the same physical package
    as the core whose id is used in the function call
    @param: core    id of core
    @return:        list of core ids that all belong to the same physical package
    """
    return util.parse_int_list(
        util.read_file(f"/sys/devices/system/cpu/cpu{core}/topology/core_siblings_list")
    )
