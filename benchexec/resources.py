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
from typing import Generator, Optional, List, Dict

from benchexec import util

__all__ = [
    "check_memory_size",
    "get_cpu_cores_per_run",
    "get_memory_banks_per_run",
    "get_cpu_package_for_core",
]

# typing defintions
_2DIntList = List[List[int]]
HierarchyLevel = Dict[int, List[int]]

FREQUENCY_FILTER_THRESHOLD = 0.95
"""Fraction of highest CPU frequency that is still allowed"""


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
    @param: coreRequirement     minimum number of cores to be reserved for each execution run
    @return:                    list of lists, where each inner list contains the cores for one run
    """

    assert coreLimit >= 1
    assert num_of_threads >= 1

    hierarchy_levels = []
    try:
        # read list of available CPU cores (int)
        allCpus_list = get_cpu_list(my_cgroups, coreSet)

        # check if all HT siblings are available for benchexec
        all_siblings = set(get_siblings_of_cores(allCpus_list))
        unavailable_siblings = all_siblings.difference(allCpus_list)
        if unavailable_siblings:
            sys.exit(
                f"Core assignment is unsupported because sibling cores "
                f"{unavailable_siblings} are not usable. "
                f"Please always make all virtual cores of a physical core available."
            )

        # read information about various topology levels

        cores_of_physical_cores = read_topology_level(
            allCpus_list, "Physical cores", "core_id"
        )

        levels_to_add = [
            cores_of_physical_cores,
            *read_cache_levels(allCpus_list),
            read_topology_level(
                allCpus_list, "Physical packages", "physical_package_id"
            ),
            read_topology_level(allCpus_list, "Dies", "die_id"),
            read_topology_level(allCpus_list, "Clusters", "cluster_id"),
            read_topology_level(allCpus_list, "Drawers", "drawer_id"),
            read_topology_level(allCpus_list, "Books", "book_id"),
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

    def compare_hierarchy_by_dict_length(level: HierarchyLevel):
        """comparator function for number of elements in a dict's value list"""
        return len(next(iter(level.values())))

    hierarchy_levels.sort(key=compare_hierarchy_by_dict_length, reverse=False)
    # sort hierarchy_levels (list of dicts) according to the dicts' value sizes

    # add root level at the end to have one level with a single node
    hierarchy_levels.append(get_root_level(hierarchy_levels))

    hierarchy_levels = filter_duplicate_hierarchy_levels(hierarchy_levels)

    assert hierarchy_levels[0] == cores_of_physical_cores

    return get_cpu_distribution(
        coreLimit,
        num_of_threads,
        use_hyperthreading,
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
    if not hierarchy_levels:
        return []

    # the first level (=> all CPU cores) cannot be a duplicate yet and is always included
    filtered_list = [hierarchy_levels[0]]

    # we compare all adjacent levels with each other...
    for i in range(len(hierarchy_levels) - 1):
        current_level = hierarchy_levels[i]
        next_level = hierarchy_levels[i + 1]

        current_values_set = [set(values) for values in current_level.values()]
        next_values_set = [set(values) for values in next_level.values()]

        # ... whether they contain either the same lists or just permutations of it
        if current_values_set == next_values_set:
            continue

        filtered_list.append(next_level)

    return filtered_list


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


def check_internal_validity(
    allCpus: Dict[int, VirtualCore],
    hierarchy_levels: List[HierarchyLevel],
):
    def all_equal(items):
        first = next(items)
        return all(first == item for item in items)

    def is_sorted(items):
        return sorted(items) == list(items)

    # TODO check whether this assertion holds and/or is required
    # assert is_sorted(allCpus.keys()), "CPUs are not sorted"  #noqa: E800

    node_count_per_level = [len(level) for level in hierarchy_levels]
    assert node_count_per_level[-1] == 1, "Root level is missing"
    assert (
        sorted(node_count_per_level, reverse=True) == node_count_per_level
    ), "Levels are not sorted correctly"
    assert len(set(node_count_per_level)) == len(
        node_count_per_level
    ), "Redundant levels with same node count"
    assert next(iter(hierarchy_levels[-1].values())) == list(
        allCpus.keys()
    ), "Root level has different cores"

    for level in hierarchy_levels:
        cores_on_level = list(itertools.chain.from_iterable(level.values()))
        # cores_on_level needs to be a permutation of allCpus.keys()
        assert len(cores_on_level) == len(allCpus), "Level has different core count"
        assert set(cores_on_level) == allCpus.keys(), "Level has different cores"
        # TODO check whether this assertion holds and/or is required
        # assert all(
        #    is_sorted(cores) for cores in level.values()
        # ), "Level has node with unsorted cores"
        assert all_equal(
            len(cores) for cores in level.values()
        ), "Level has nodes with different sizes"


def get_cpu_distribution(
    core_limit: int,
    num_of_threads: int,
    use_hyperthreading: bool,
    hierarchy_levels: List[HierarchyLevel],
    core_requirement: Optional[int] = None,
) -> List[List[int]]:
    """
    Implements optional restrictions and calls the actual assignment function

    @param: core_limit          the number of cores for each parallel benchmark execution
    @param: num_of_threads      the number of parallel benchmark executions
    @param: use_hyperthreading  boolean to check if no-hyperthreading method is being used
    @param: hierarchy_levels    list of dicts of lists: each dict in the list corresponds to one topology layer and maps from the identifier read from the topology to a list of the cores belonging to it
    @param: core_requirement    minimum number of cores to be reserved for each execution run
    @return:                    list of lists, where each inner list contains the cores for one run
    """

    # creates a dict of VirtualCore objects from core ID list
    allCpus = {
        core: VirtualCore(core, [])
        for core in itertools.chain.from_iterable(hierarchy_levels[-1].values())
    }

    for level in hierarchy_levels:  # hierarchy_levels (list of dicts)
        for key, cores in level.items():
            for core in cores:
                allCpus[core].memory_regions.append(
                    key
                )  # memory_regions is a list of keys

    check_internal_validity(allCpus, hierarchy_levels)
    result = []

    # no HT filter: delete all but the key core from hierarchy_levels
    if not use_hyperthreading:
        filter_hyperthreading_siblings(allCpus, hierarchy_levels)
        check_internal_validity(allCpus, hierarchy_levels)

    if not core_requirement:
        result = core_allocation_algorithm(
            core_limit,
            num_of_threads,
            allCpus,
            hierarchy_levels,
        )
    else:
        if core_requirement >= core_limit:
            # reserves core_requirement number of cores of which coreLimit is used
            prelim_result = core_allocation_algorithm(
                core_requirement,
                num_of_threads,
                allCpus,
                hierarchy_levels,
            )
            for resultlist in prelim_result:
                result.append(resultlist[:core_limit])
        else:
            max_possible_cores = core_limit
            while max_possible_cores > core_requirement:
                # uses as many cores as possible (with maximum coreLimit), but at least core_requirement num of cores
                if check_distribution_feasibility(
                    max_possible_cores,
                    num_of_threads,
                    hierarchy_levels,
                    isTest=True,
                ):
                    break
                else:
                    max_possible_cores -= 1
            result = core_allocation_algorithm(
                max_possible_cores,
                num_of_threads,
                allCpus,
                hierarchy_levels,
            )
    return result


def filter_hyperthreading_siblings(
    allCpus: Dict[int, VirtualCore],
    hierarchy_levels: List[HierarchyLevel],
) -> None:
    """
    Deletes all but one hyperthreading sibling per physical core out of allCpus and
    hierarchy_levels.
    @param: allCpus             list of VirtualCore objects
    @param: hierarchy_levels    list of dicts of lists: each dict in the list corresponds to one topology layer and maps from the identifier read from the topology to a list of the cores belonging to it
    """
    if not hierarchy_levels:
        return

    cores_to_remove = set()

    # hierarchy_levels[0] is the lowest layer containing all CPU cores, including hyperthreading ones.
    # each value in it represents a physical core and is a list with all hyperthreading cores on this physical core
    for sibling_group in hierarchy_levels[0].values():
        # we only want to keep one hyperthreading core => we add all but the first to the removal list
        cores_to_remove.update(sibling_group[1:])

    # the removed cores are still in the hierarchy and need to be removed, not only on the first layer,
    # but all layers
    for core in cores_to_remove:
        if core in allCpus:
            current_regions = allCpus[core].memory_regions
            del allCpus[core]

            for i, region in enumerate(current_regions):
                level = hierarchy_levels[i]
                if core in level.get(region, []):
                    level[region].remove(core)
                    if not level[region]:
                        # empty group
                        del level[region]


def check_distribution_feasibility(
    coreLimit: int,
    num_of_threads: int,
    hierarchy_levels: List[HierarchyLevel],
    isTest: bool = True,
) -> bool:
    """
    Checks, whether the core distribution can work with the given parameters

    @param: coreLimit           the number of cores for each parallel benchmark execution
    @param: num_of_threads      the number of parallel benchmark executions
    @param: hierarchy_levels    list of dicts of lists: each dict in the list corresponds to one topology layer and maps from the identifier read from the topology to a list of the cores belonging to it
    @param: isTest              boolean whether the check is used to test the coreLimit or for the actual core allocation
    @return:                    list of lists, where each inner list contains the cores for one run
    """
    is_feasible = True

    # compare number of available cores to required cores per run
    coreCount = len(next(iter(hierarchy_levels[-1].values())))
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

    coreLimit_rounded_up = calculate_coreLimit_rounded_up(hierarchy_levels, coreLimit)
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

    def next_level_suitable(chosen_level, hierarchy_levels, core_limit):
        """Check if its possible to proceed to the next hierarchy level."""
        if chosen_level >= len(hierarchy_levels) - 1:
            return False  # Already at the last level
        current_level_values = next(iter(hierarchy_levels[chosen_level].values()))
        return len(current_level_values) < core_limit

    chosen_level = 1
    # move up in hierarchy as long as the number of cores at the current level is smaller than the coreLimit
    # if the number of cores at the current level is as big as the coreLimit: exit loop
    while next_level_suitable(chosen_level, hierarchy_levels, coreLimit_rounded_up):
        chosen_level = chosen_level + 1
    return chosen_level


def calculate_coreLimit_rounded_up(
    hiearchy_levels: List[HierarchyLevel], coreLimit: int
) -> int:
    """
    coreLimit_rounded_up (int): recalculate # cores for each run accounting for HT

    @param: hierarchy_levels    list of dicts of lists: each dict in the list corresponds to one topology layer and
                                maps from the identifier read from the topology to a list of the cores belonging to it
    @param: coreLimit           the number of cores for each parallel benchmark execution
    @return:                    rounding up the coreLimit to a multiple of the num of hyper-threading siblings per core
    """
    # Always use full physical cores.
    core_size = len(next(iter(hiearchy_levels[0].values())))
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


def get_root_level(hierarchy_levels: List[HierarchyLevel]) -> HierarchyLevel:
    """
    Creates a "meta" or "root" level that includes all cores.
    This is necessary to iterate through all cores if the highest hierarchy level consists of more than one unit.
    @param: hierarchy_levels    list of dicts of lists: each dict in the list corresponds to one topology layer and
                                maps from the identifier read from the topology to a list of the cores belonging to it
    @return: a hierachy level with all cores in a single node
    """
    all_cores = list(itertools.chain.from_iterable(hierarchy_levels[-1].values()))
    return {0: all_cores}


def get_core_units_on_level(
    allCpus: Dict[int, VirtualCore], cores: List[int], hLevel: int
) -> Dict[int, List[int]]:
    """
    Partitions a given list of cores according to which topological unit they belong to
    on a given hierarchy level.

    @param: allCpus       VirtualCore instances for every core id
    @param: cores         list of core ids
    @param: hLevel        the index of the hierarchy level to search in
    """

    result = {}
    for core in cores:
        unit_key = allCpus[core].memory_regions[hLevel]
        result.setdefault(unit_key, []).append(core)
    return result


def core_allocation_algorithm(
    coreLimit: int,
    num_of_threads: int,
    allCpus: Dict[int, VirtualCore],
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
    @param: hierarchy_levels    list of dicts mapping from a memory region identifier to its belonging cores
    @return result:             list of lists each containing the cores assigned to the same thread
    """

    def _find_spreading_memory_region_key(
        allCpus: Dict[int, VirtualCore],
        chosen_level: int,
        hierarchy_levels: List[HierarchyLevel],
    ) -> tuple[int, HierarchyLevel]:
        # we start from the highest hierarchy level
        search_current_level = len(hierarchy_levels) - 1
        distribution_dict = hierarchy_levels[search_current_level]

        while search_current_level > 0:
            if is_symmetric_hierachy(distribution_dict):
                # for symmetric ones, we go further into the hierarchy (and only return them if we are at the end of the hierarchy already)
                search_current_level -= 1
                distribution_dict = hierarchy_levels[search_current_level]
            else:
                largest_core_subset = max(distribution_dict.values(), key=len)
                distribution_dict = get_core_units_on_level(
                    allCpus, largest_core_subset, search_current_level - 1
                )

                if is_symmetric_hierachy(distribution_dict):
                    if search_current_level > chosen_level:
                        while (
                            search_current_level >= chosen_level
                            and search_current_level > 0
                        ):
                            search_current_level -= 1
                            largest_core_subset = max(
                                distribution_dict.values(), key=len
                            )
                            distribution_dict = get_core_units_on_level(
                                allCpus, largest_core_subset, search_current_level - 1
                            )
                    break
                else:
                    search_current_level -= 1

        # we only need the memory region, thus we just take the first core, doesn't matter
        first_core = list(distribution_dict.values())[0][0]
        spreading_memory_region_key = allCpus[first_core].memory_regions[chosen_level]
        return spreading_memory_region_key, distribution_dict

    # check whether the distribution can work with the given parameters
    check_distribution_feasibility(
        coreLimit,
        num_of_threads,
        hierarchy_levels,
        isTest=False,
    )

    # check if all units of the same hierarchy level have the same number of cores
    for hierarchy_level in hierarchy_levels:
        if not is_symmetric_hierachy(hierarchy_level):
            sys.exit(
                "Asymmetric machine architecture not supported: "
                "CPUs/memory regions with different number of cores."
            )

    # coreLimit_rounded_up (int): recalculate # cores for each run accounting for HT
    coreLimit_rounded_up = calculate_coreLimit_rounded_up(hierarchy_levels, coreLimit)
    # Choose hierarchy level for core assignment
    chosen_level = calculate_chosen_level(hierarchy_levels, coreLimit_rounded_up)
    # calculate how many sub_units have to be used to accommodate the runs_per_unit
    sub_units_per_run = calculate_sub_units_per_run(
        coreLimit_rounded_up, hierarchy_levels, chosen_level
    )

    # Start core assignment algorithm
    result = []
    active_hierarchy_level = hierarchy_levels[chosen_level]
    while len(result) < num_of_threads:  # and i < len(active_hierarchy_level):
        """
        for each new thread, the algorithm searches the hierarchy_levels for a
        dict with an unequal number of cores, chooses the value list with the most cores and
        compiles a child dict with these cores, then again choosing the value list with the most cores ...
        until the value lists have the same length.
        Thus the algorithm finds the index search_current_level for hierarchy_levels that indicates the dict
        from which to continue the search for the cores with the highest distance from the cores
        assigned before
        """

        spreading_memory_region_key, distribution_dict = (
            _find_spreading_memory_region_key(allCpus, chosen_level, hierarchy_levels)
        )
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
                assignment_current_level = chosen_level - 1
                if assignment_current_level - 1 > 0:
                    assignment_current_level -= 1

                child_dict = get_core_units_on_level(
                    allCpus, sub_unit_cores.copy(), assignment_current_level
                )
                """
                searches for the key-value pair that already provided cores for the assignment
                and therefore has the fewest elements in its value list while non-empty,
                and returns one of the cores in this key-value pair.
                If no cores have been assigned yet, any core can be chosen and the next best core is returned.
                """
                while assignment_current_level > 0:
                    if is_symmetric_hierachy(child_dict):
                        break
                    else:
                        assignment_current_level -= 1
                        distribution_list = list(child_dict.values())
                        for iter2 in distribution_list.copy():
                            if len(iter2) == 0:
                                distribution_list.remove(iter2)
                        distribution_list.sort(reverse=False)
                        child_dict = get_core_units_on_level(
                            allCpus, distribution_list[0], assignment_current_level
                        )
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
                    remove_core_from_hierarchy_levels(core, allCpus, hierarchy_levels)

            while sub_unit_cores:
                remove_core_from_hierarchy_levels(
                    sub_unit_cores[0], allCpus, hierarchy_levels
                )
                # active_cores & sub_unit_cores are deleted as well since they're just pointers
                # to hierarchy_levels

            # if coreLimit reached: append core to result, delete remaining cores from active_cores
            if len(cores) == coreLimit:
                result.append(cores)

    # cleanup: while-loop stops before running through all units: while some active_cores-lists
    # & sub_unit_cores-lists are empty, other stay half-full or full
    logging.debug("Core allocation: %s", result)
    return result


def is_symmetric_hierachy(hierarchy_level: HierarchyLevel) -> bool:
    """
    returns True if the number of values in the lists of the key-value pairs
    is equal throughout the dict

    @param: hierarchy_levels    list of dicts of lists: each dict in the list corresponds to one topology layer and
                                maps from the identifier read from the topology to a list of the cores belonging to it
    @return:                    true if symmetric
    """
    cores_per_unit = len(next(iter(hierarchy_level.values())))
    return all(len(cores) == cores_per_unit for cores in hierarchy_level.values())


def remove_core_from_hierarchy_levels(
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
    for mem_index, region in enumerate(current_core_regions):
        core_list = hierarchy_levels[mem_index][region]
        if core in core_list:
            core_list.remove(core)
            if not core_list:  # empty memory region, which we can delete
                hierarchy_levels[mem_index].pop(region, None)


def get_cpu_list(my_cgroups, coreSet: Optional[List] = None) -> List[int]:
    """
    retrieves all cores available to the users cgroup.
    If a coreSet is provided, the list of all available cores is reduced to those cores
    that are in both - available cores and coreSet.
    A filter is applied to make sure that all used cores run roughly at the same
    clock speed (allowing within FREQUENCY_FILTER_THRESHOLD from the highest frequency)
    @param coreSet list of cores to be used in the assignment as specified by the user
    @return list of available cores
    """
    # read list of available CPU cores
    cpus = my_cgroups.read_allowed_cpus()

    # Filter CPU cores according to the list of identifiers provided by a user
    if coreSet:
        invalid_cores = sorted(set(coreSet).difference(cpus))
        if invalid_cores:
            raise ValueError(
                "The following provided CPU cores are not available: "
                + ", ".join(map(str, invalid_cores))
            )
        cpus = [core for core in cpus if core in coreSet]

    cpu_max_frequencies = read_generic_reverse_mapping(
        cpus, "CPU frequency", "/sys/devices/system/cpu/cpu{}/cpufreq/cpuinfo_max_freq"
    )
    fastest_cpus = frequency_filter(cpu_max_frequencies)
    logging.debug("List of available CPU cores is %s.", fastest_cpus)
    return fastest_cpus


def frequency_filter(cpu_max_frequencies: Dict[int, List[int]]) -> List[int]:
    """
    Filters the available CPU cores so that only the fastest cores remain.
    Only cores with a maximal frequency above the defined threshold
    (FREQUENCY_FILTER_THRESHOLD times the maximal frequency of the fastest core)
    are returned for further use.

    @param: cpu_max_frequencies mapping from frequencies to core ids
    @return: list with the ids of the fastest cores
    """
    freq_threshold = max(cpu_max_frequencies.keys()) * FREQUENCY_FILTER_THRESHOLD
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
            "Unused cores due to frequency less than %s%% of fastest core (%s): %s",
            FREQUENCY_FILTER_THRESHOLD * 100,
            fastest,
            slow_cores,
        )
    return filtered_allCpus_list


def read_generic_reverse_mapping(
    ids: List[int],
    name,
    path_template: str,
) -> Dict[int, List[int]]:
    """
    Given a list of ids and a path template, read an int value for every id,
    and return a reverse mapping (from value to id).

    @param: ids list of ids to be inserted into the path template
    @param: name name of the mapping to be read (for debug messages)
    @param: path_template path template compatible with str.format()
    @return: mapping of read int values to the ids for which they were read
    """

    mapping = {}
    try:
        for i in ids:
            value = int(util.read_file(path_template.format(i)))
            mapping.setdefault(value, []).append(i)
    except FileNotFoundError:
        logging.debug("%s information not available at %s.", name, path_template)
        return {}
    return mapping


def read_topology_level(
    allCpus_list: List[int], name: str, filename: str
) -> HierarchyLevel:
    """Read one level of the CPU code topology information provided by the kernel."""
    return read_generic_reverse_mapping(
        allCpus_list, name, "/sys/devices/system/cpu/cpu{}/topology/" + filename
    )


def get_siblings_of_cores(allCpus_list: List[int]) -> Generator[int, None, None]:
    """
    Get hyperthreading siblings from core_cpus_list or thread_siblings_list (deprecated).

    @param: allCpus_list    list of cpu Ids to be read
    @return:                list of all siblings of all given cores
    """
    path = "/sys/devices/system/cpu/cpu{}/topology/{}"
    usePath = ""
    # if no hyperthreading available, the siblings list contains only the core itself
    if os.path.isfile(path.format(allCpus_list[0], "core_cpus_list")):
        usePath = "core_cpus_list"
    elif os.path.isfile(path.format(allCpus_list[0], "thread_siblings_list")):
        usePath = "thread_siblings_list"
    else:
        raise ValueError("No siblings information accessible")

    for core in allCpus_list:
        yield from util.parse_int_list(util.read_file(path.format(core, usePath)))


def get_group_mapping(cores_of_NUMA_region: HierarchyLevel) -> HierarchyLevel:
    """
    Generates a mapping from groups to their corresponding cores.

    @param: allCpus_list    list of cpu Ids to be read
    @return:                mapping of group id to list of cores (dict)
    """
    nodes_of_groups = {}

    try:
        # generates dict of all available nodes with their group nodes
        for node_id in sorted(cores_of_NUMA_region):
            group = get_nodes_of_group(node_id)
            nodes_of_groups[node_id] = frozenset(group)

    except FileNotFoundError:
        logging.warning(
            "Information on node distances not available at /sys/devices/system/node/nodeX/distance"
        )
        return {}

    groups_dict = {}
    next_group_id = 0

    # we merge identical sets & detect overlaps
    for node_id, node_set in nodes_of_groups.items():
        # do we have conflicting (partial) overlap of two different sets? => error
        for existing_set in groups_dict:
            overlap = existing_set.intersection(node_set)
            if overlap and existing_set != node_set:
                raise Exception(
                    "Non-conclusive system information: overlapping node groups"
                )

        # if not already in set, add it and give it the next group id
        if node_set not in groups_dict:
            groups_dict[node_set] = next_group_id
            next_group_id += 1

    # for each distict node set, we gather all corresponding cores into a single group
    cores_of_groups = {}
    for node_set, group_id in groups_dict.items():
        group_cores = []
        for nid in node_set:
            group_cores.extend(cores_of_NUMA_region[nid])
        cores_of_groups[group_id] = group_cores

    logging.debug("Groups of cores are %s.", cores_of_groups)
    return cores_of_groups


def get_nodes_of_group(node_id: int) -> List[int]:
    """
    returns the nodes that belong to the same group because they have a smaller distance
    between each other than to rest of the nodes

    @param: node_id
    @return:list of nodes of the group that the node_id belongs to
    """
    distance_list = [
        int(dist)
        for dist in util.read_file(
            f"/sys/devices/system/node/node{node_id}/distance"
        ).split(" ")
    ]
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
    if len(distance_list) == 1:
        # single node
        return [0]
    sorted_distance_list = sorted(distance_list)
    smallest_distance = sorted_distance_list[0]
    second_smallest = sorted_distance_list[1]
    greatest_distance = sorted_distance_list[-1]
    # we assume that all other nodes are slower to access than the core itself
    assert second_smallest > smallest_distance, "More than one smallest distance"

    group_list = [distance_list.index(smallest_distance)]
    if second_smallest != greatest_distance:
        for index, dist in enumerate(distance_list):
            if dist == second_smallest:
                group_list.append(index)
    return group_list  # [0 1 2 3]


def read_cache_levels(allCpus_list: List[int]) -> Generator[HierarchyLevel, None, None]:
    """
    Generates mappings from cache ids to the corresponding cores.
    One mapping is created for each cache level.

    @param: allCpus_list    list of cpu Ids to be read
    @return:                generator of hiearchy levels
    """
    dir_path = "/sys/devices/system/cpu/cpu{}/cache"
    # pick caches available for first core and assume all cores have the same caches
    cache_names = [
        entry
        for entry in os.listdir(dir_path.format(allCpus_list[0]))
        if entry.startswith("index")
    ]
    for cache in cache_names:
        yield read_generic_reverse_mapping(
            allCpus_list, f"Cache {cache}", f"{dir_path}/{cache}/id"
        )


def get_NUMA_mapping(allCpus_list: List[int]) -> HierarchyLevel:
    """
    Generates a mapping from a Numa Region to its corresponding cores.

    @param: allCpus_list    list of cpu Ids to be read
    @return:                mapping of Numa Region id to list of cores (dict)
    """
    cores_of_NUMA_region = {}
    for core in allCpus_list:
        coreDir = f"/sys/devices/system/cpu/cpu{core}/"
        NUMA_regions = _get_memory_banks_listed_in_dir(coreDir)
        if NUMA_regions:
            cores_of_NUMA_region.setdefault(NUMA_regions[0], []).append(core)
            # adds core to value list at key [NUMA_region[0]]
        else:
            # If some cores do not have NUMA information, skip using it completely
            logging.warning(
                "Kernel does not have NUMA support. Use benchexec at your own risk."
            )
            return {}
    logging.debug("Memory regions of cores are %s.", cores_of_NUMA_region)
    return cores_of_NUMA_region


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
