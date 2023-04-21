# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import logging
import sys
import unittest
import math
from collections import defaultdict
from functools import cmp_to_key
from resources import get_cpu_distribution, virtualCore, check_and_add_meta_level

sys.dont_write_bytecode = True  # prevent creation of .pyc files


def lrange(start, end):
    return list(range(start, end))


class TestCpuCoresPerRun(unittest.TestCase):
    num_of_cores = 0
    num_of_packages = 0
    num_of_groups = 0
    num_of_NUMAs = 0
    num_of_L3_regions = 0
    num_of_hyperthreading_siblings = 0

    @classmethod
    def setUpClass(cls):
        cls.longMessage = True
        logging.disable(logging.CRITICAL)

    def assertValid(self, coreLimit, num_of_threads, expectedResult=None):
        result = get_cpu_distribution(
            coreLimit, num_of_threads, self.use_hyperthreading, *self.machine()
        )
        if expectedResult:
            self.assertEqual(
                expectedResult,
                result,
                f"Incorrect result for {coreLimit} cores and {num_of_threads} threads.",
            )

    def assertInvalid(self, coreLimit, num_of_threads):
        self.assertRaises(
            SystemExit,
            get_cpu_distribution,
            coreLimit,
            num_of_threads,
            self.use_hyperthreading,
            *self.machine(),
        )

    def assertEqualResult(self, coreLimit, num_of_threads, expectedResult=None):
        result = get_cpu_distribution(
            coreLimit, num_of_threads, self.use_hyperthreading, *self.machine()
        )
        if expectedResult:
            self.assertEqual(
                expectedResult,
                result,
                f"Incorrect result for {coreLimit} cores and {num_of_threads} threads.",
            )

    def machine(self):
        """Create the necessary parameters of get_cpu_distribution for a specific machine."""

        allCpus = {}
        siblings_of_core = defaultdict(list)
        cores_of_L3cache = defaultdict(list)
        cores_of_NUMA_Region = defaultdict(list)
        cores_of_group = defaultdict(list)
        cores_of_package = defaultdict(list)
        hierarchy_levels = []

        for cpu_nr in range(self.num_of_cores):
            # package
            if self.num_of_packages and self.num_of_packages != 0:
                packageNr = math.trunc(
                    cpu_nr / (self.num_of_cores / self.num_of_packages)
                )
                cores_of_package[packageNr].append(cpu_nr)

            # groups
            if self.num_of_groups and self.num_of_groups != 0:
                groupNr = math.trunc(cpu_nr / (self.num_of_cores / self.num_of_groups))
                cores_of_group[groupNr].append(cpu_nr)

            # numa
            if self.num_of_NUMAs and self.num_of_NUMAs != 0:
                numaNr = math.trunc(cpu_nr / (self.num_of_cores / self.num_of_NUMAs))
                cores_of_NUMA_Region[numaNr].append(cpu_nr)

            # L3
            if self.num_of_L3_regions and self.num_of_L3_regions != 0:
                l3Nr = math.trunc(cpu_nr / (self.num_of_cores / self.num_of_L3_regions))
                cores_of_L3cache[l3Nr].append(cpu_nr)

            # hyper-threading siblings
            siblings = list(
                range(
                    (math.trunc(cpu_nr / self.num_of_hyperthreading_siblings))
                    * self.num_of_hyperthreading_siblings,
                    (math.trunc(cpu_nr / self.num_of_hyperthreading_siblings) + 1)
                    * self.num_of_hyperthreading_siblings,
                )
            )
            siblings_of_core.update({cpu_nr: siblings})

        cleanList = []
        for core in siblings_of_core:
            if core not in cleanList:
                for sibling in siblings_of_core[core]:
                    if sibling != core:
                        cleanList.append(sibling)
        for element in cleanList:
            siblings_of_core.pop(element)

        for item in [
            siblings_of_core,
            cores_of_L3cache,
            cores_of_NUMA_Region,
            cores_of_package,
            cores_of_group,
        ]:
            if len(item) > 0:
                hierarchy_levels.append(item)

        # sort hierarchy_levels:
        def compare_hierarchy(dict1, dict2):
            value1 = len(next(iter(dict1.values())))
            value2 = len(next(iter(dict2.values())))
            if value1 > value2:
                return 1
            elif value1 < value2:
                return -1
            else:
                return 0

        hierarchy_levels.sort(
            key=cmp_to_key(compare_hierarchy)
        )  # hierarchy_level = [dict1, dict2, dict3]

        allCpus_list = list(range(self.num_of_cores))

        for cpu_nr in allCpus_list:
            allCpus.update({cpu_nr: virtualCore(cpu_nr, [])})
        for level in hierarchy_levels:  # hierarchy_levels = [dict1, dict2, dict3]
            for key in level:
                for core in level[key]:
                    allCpus[core].memory_regions.append(key)

        check_and_add_meta_level(hierarchy_levels, allCpus)

        return allCpus, siblings_of_core, hierarchy_levels

    def t_unit_assertValid(self, coreLimit, expectedResult, maxThreads=None):
        self.coreLimit = coreLimit
        if maxThreads:
            threadLimit = maxThreads
        else:
            if not self.use_hyperthreading:
                threadLimit = math.floor(
                    self.num_of_cores
                    / math.ceil(self.coreLimit * self.num_of_hyperthreading_siblings)
                )
            else:
                threadLimit = math.floor(
                    self.num_of_cores
                    / (
                        math.ceil(self.coreLimit / self.num_of_hyperthreading_siblings)
                        * self.num_of_hyperthreading_siblings
                    )
                )
        num_of_threads = 1
        while num_of_threads <= threadLimit:
            self.assertValid(
                self.coreLimit, num_of_threads, expectedResult[:num_of_threads]
            )
            num_of_threads = num_of_threads + 1

    # expected order in which cores are used for runs with coreLimit==1/2/3/4/8, used by the following tests
    # these fields should be filled in by subclasses to activate the corresponding tests
    # (same format as the expected return value by _get_cpu_cores_per_run)
    oneCore_assignment = None
    twoCore_assignment = None
    threeCore_assignment = None
    fourCore_assignment = None
    eightCore_assignment = None
    use_hyperthreading = True

    """def test_singleThread(self):
        # test all possible coreLimits for a single thread
        self.t_unit_assertValid (1, self.oneCore_assignment)"""

    def test_oneCorePerRun(self):
        # test all possible numOfThread values for runs with one core
        self.t_unit_assertValid(1, self.oneCore_assignment)

    def test_twoCoresPerRun(self):
        # test all possible numOfThread values for runs with two cores
        self.t_unit_assertValid(2, self.twoCore_assignment)

    def test_threeCoresPerRun(self):
        # test all possible numOfThread values for runs with three cores
        self.t_unit_assertValid(3, self.threeCore_assignment)

    def test_fourCoresPerRun(self):
        # test all possible numOfThread values for runs with four cores
        self.t_unit_assertValid(4, self.fourCore_assignment)

    def test_eightCoresPerRun(self):
        # test all possible numOfThread values for runs with eight cores
        self.t_unit_assertValid(8, self.eightCore_assignment)


class Test_Topology_P1_NUMA2_L8_C16_F(TestCpuCoresPerRun):
    num_of_cores = 16
    num_of_packages = 1
    num_of_NUMAs = 2
    num_of_L3_regions = 8
    num_of_hyperthreading_siblings = 2
    use_hyperthreading = False

    """                 x

            x                       x

    x   x       x   x       x   x      x    x

    x-  x-      x-  x-      x-  x-     x-  x-
    """
    # expected results for different coreLimits
    oneCore_assignment = [[x] for x in [0, 8, 2, 10, 4, 12, 6, 14]]
    twoCore_assignment = [[0, 2], [8, 10], [4, 6], [12, 14]]
    threeCore_assignment = [[0, 2, 4], [8, 10, 12]]
    fourCore_assignment = [[0, 2, 4, 6], [8, 10, 12, 14]]
    fiveCore_assignment = [[0, 2, 4, 6, 8]]
    eightCore_assignment = [[0, 2, 4, 6, 8, 10, 12, 14]]

    def test_fiveCoresPerRun(self):
        self.t_unit_assertValid(5, self.fiveCore_assignment)

    def test_invalid(self):
        # coreLimit, num_of_threads
        self.assertInvalid(2, 5)
        self.assertInvalid(5, 2)
        self.assertInvalid(3, 3)


class Test_Topology_P1_NUMA2_L8_C16_T(TestCpuCoresPerRun):
    num_of_cores = 16
    num_of_packages = 1
    num_of_NUMAs = 2
    num_of_L3_regions = 8
    num_of_hyperthreading_siblings = 2
    use_hyperthreading = True

    # expected results for different coreLimits
    oneCore_assignment = [[x] for x in [0, 8, 2, 10, 4, 12, 6, 14]]
    twoCore_assignment = [
        [0, 1],
        [8, 9],
        [2, 3],
        [10, 11],
        [4, 5],
        [12, 13],
        [6, 7],
        [14, 15],
    ]
    threeCore_assignment = [[0, 1, 2], [8, 9, 10], [4, 5, 6], [12, 13, 14]]
    fourCore_assignment = [[0, 1, 2, 3], [8, 9, 10, 11], [4, 5, 6, 7], [12, 13, 14, 15]]
    eightCore_assignment = [[0, 1, 2, 3, 4, 5, 6, 7], [8, 9, 10, 11, 12, 13, 14, 15]]

    def test_singleCPU_invalid(self):
        # coreLimit, num_of_threads
        self.assertInvalid(2, 9)
        self.assertInvalid(4, 5)
        self.assertInvalid(3, 5)


class Test_Topology_P1_NUMA3_L6_C12_F(TestCpuCoresPerRun):
    num_of_packages = 1
    num_of_NUMAs = 3
    num_of_L3_regions = 6
    num_of_cores = 12
    num_of_hyperthreading_siblings = 2
    use_hyperthreading = False
    """                             x                                           P

            x                       x                       x                   NUMA

        x       x               x       x               x       x               L3

    0   (1)     2   (3)     4   (5)     6   (7)     8   (9)     10     (11)     cores
    """
    # expected results for different coreLimits
    oneCore_assignment = [[x] for x in [0, 4, 8, 2, 6, 10]]
    twoCore_assignment = [[0, 2], [4, 6], [8, 10]]
    threeCore_assignment = [[0, 2, 4]]  # ,[8,10,6]
    fourCore_assignment = [[0, 2, 4, 6]]

    def test_threeCoresPerRun(self):
        self.t_unit_assertValid(3, self.threeCore_assignment, 1)

    def test_singleCPU_invalid(self):
        # coreLimit, num_of_threads
        self.assertInvalid(2, 4)
        self.assertInvalid(3, 2)
        self.assertInvalid(4, 2)


class Test_Topology_P1_NUMA3_L6_C12_T(TestCpuCoresPerRun):
    num_of_packages = 1
    num_of_NUMAs = 3
    num_of_L3_regions = 6
    num_of_cores = 12
    num_of_hyperthreading_siblings = 2
    use_hyperthreading = True
    """                             x                                           P

            x                       x                       x                   NUMA

        x       x               x       x               x       x               L3

    0   1     2    3        4     5     6   7       8   9     10    11          cores
    """

    # expected results for different coreLimits
    oneCore_assignment = [[x] for x in [0, 4, 8, 2, 6, 10]]
    twoCore_assignment = [[0, 1], [4, 5], [8, 9], [2, 3], [6, 7], [10, 11]]
    threeCore_assignment = [[0, 1, 2], [4, 5, 6], [8, 9, 10]]
    fourCore_assignment = [[0, 1, 2, 3], [4, 5, 6, 7], [8, 9, 10, 11]]
    fiveCore_assignment = [[0, 1, 2, 3, 4]]  # ,[8,9,10,11,6]]
    eightCore_assignment = [[0, 1, 2, 3, 4, 5, 6, 7]]

    def test_threeCoresPerRun(self):
        self.t_unit_assertValid(5, self.fiveCore_assignment, 1)

    def test_singleCPU_invalid(self):
        # coreLimit, num_of_threads
        self.assertInvalid(2, 7)
        self.assertInvalid(3, 4)
        self.assertInvalid(4, 4)
        self.assertInvalid(5, 2)


class Test_Topology_P2_NUMA4_L8_C16_F(TestCpuCoresPerRun):
    num_of_packages = 2
    num_of_NUMAs = 4
    num_of_L3_regions = 8
    num_of_cores = 16
    num_of_hyperthreading_siblings = 2
    use_hyperthreading = False

    # expected results for different coreLimits
    oneCore_assignment = [[x] for x in [0, 8, 4, 12, 2, 10, 6, 14]]
    twoCore_assignment = [[0, 2], [8, 10], [4, 6], [12, 14]]
    threeCore_assignment = [[0, 2, 4], [8, 10, 12]]
    fourCore_assignment = [[0, 2, 4, 6], [8, 10, 12, 14]]
    eightCore_assignment = [[0, 2, 4, 6, 8, 10, 12, 14]]

    def test_singleCPU_invalid(self):
        # coreLimit, num_of_threads
        self.assertInvalid(2, 5)
        self.assertInvalid(3, 3)
        self.assertInvalid(4, 3)
        self.assertInvalid(8, 2)


class Test_Topology_P2_NUMA4_L8_C16_T(TestCpuCoresPerRun):
    num_of_packages = 2
    num_of_NUMAs = 4
    num_of_L3_regions = 8
    num_of_cores = 16
    num_of_hyperthreading_siblings = 2
    use_hyperthreading = True

    # expected results for different coreLimits
    oneCore_assignment = [[x] for x in [0, 8, 4, 12, 2, 10, 6, 14]]
    twoCore_assignment = [
        [0, 1],
        [8, 9],
        [4, 5],
        [12, 13],
        [2, 3],
        [10, 11],
        [6, 7],
        [14, 15],
    ]
    threeCore_assignment = [[0, 1, 2], [8, 9, 10], [4, 5, 6], [12, 13, 14]]
    fourCore_assignment = [[0, 1, 2, 3], [8, 9, 10, 11], [4, 5, 6, 7], [12, 13, 14, 15]]
    eightCore_assignment = [[0, 1, 2, 3, 4, 5, 6, 7], [8, 9, 10, 11, 12, 13, 14, 15]]

    def test_singleCPU_invalid(self):
        # coreLimit, num_of_threads
        self.assertInvalid(2, 9)
        self.assertInvalid(3, 5)
        self.assertInvalid(4, 5)
        self.assertInvalid(8, 3)


class Test_Topology_P1_G2_NUMA4_L8_C16_F(TestCpuCoresPerRun):
    num_of_packages = 1
    num_of_groups = 2
    num_of_NUMAs = 4
    num_of_L3_regions = 8
    num_of_cores = 16
    num_of_hyperthreading_siblings = 2
    use_hyperthreading = False

    # expected results for different coreLimits
    oneCore_assignment = [[x] for x in [0, 8, 4, 12, 2, 10, 6, 14]]
    twoCore_assignment = [[0, 2], [8, 10], [4, 6], [12, 14]]
    threeCore_assignment = [[0, 2, 4], [8, 10, 12]]
    fourCore_assignment = [[0, 2, 4, 6], [8, 10, 12, 14]]
    eightCore_assignment = [[0, 2, 4, 6, 8, 10, 12, 14]]

    def test_singleCPU_invalid(self):
        # coreLimit, num_of_threads
        self.assertInvalid(2, 5)
        self.assertInvalid(3, 3)
        self.assertInvalid(4, 3)
        self.assertInvalid(8, 2)


class Test_Topology_P1_G2_NUMA4_L8_C16_T(TestCpuCoresPerRun):
    num_of_packages = 1
    num_of_groups = 2
    num_of_NUMAs = 4
    num_of_L3_regions = 8
    num_of_cores = 16
    num_of_hyperthreading_siblings = 2
    use_hyperthreading = True

    # expected results for different coreLimits
    oneCore_assignment = [[x] for x in [0, 8, 4, 12, 2, 10, 6, 14]]
    twoCore_assignment = [
        [0, 1],
        [8, 9],
        [4, 5],
        [12, 13],
        [2, 3],
        [10, 11],
        [6, 7],
        [14, 15],
    ]
    threeCore_assignment = [[0, 1, 2], [8, 9, 10], [4, 5, 6], [12, 13, 14]]
    fourCore_assignment = [[0, 1, 2, 3], [8, 9, 10, 11], [4, 5, 6, 7], [12, 13, 14, 15]]
    eightCore_assignment = [[0, 1, 2, 3, 4, 5, 6, 7], [8, 9, 10, 11, 12, 13, 14, 15]]

    def test_singleCPU_invalid(self):
        # coreLimit, num_of_threads
        self.assertInvalid(2, 9)
        self.assertInvalid(3, 5)
        self.assertInvalid(4, 5)
        self.assertInvalid(8, 3)


class Test_Topology_P1_NUMA2_L4_C12_F3(TestCpuCoresPerRun):
    num_of_packages = 1
    num_of_NUMAs = 2
    num_of_L3_regions = 4
    num_of_cores = 12
    num_of_hyperthreading_siblings = 3
    use_hyperthreading = False

    # expected results for different coreLimits
    oneCore_assignment = [[x] for x in [0, 6, 3, 9]]
    twoCore_assignment = [[0, 3], [6, 9]]
    threeCore_assignment = [[0, 3, 6]]
    fourCore_assignment = [[0, 3, 6, 9]]

    def test_singleCPU_invalid(self):
        # coreLimit, num_of_threads
        self.assertInvalid(2, 3)
        self.assertInvalid(3, 2)
        self.assertInvalid(4, 2)
        self.assertInvalid(8, 3)


class Test_Topology_P1_NUMA2_L4_C12_T3(TestCpuCoresPerRun):
    num_of_packages = 1
    num_of_NUMAs = 2
    num_of_L3_regions = 4
    num_of_cores = 12
    num_of_hyperthreading_siblings = 3
    use_hyperthreading = True

    # expected results for different coreLimits
    oneCore_assignment = [[x] for x in [0, 6, 3, 9]]
    twoCore_assignment = [[0, 1], [6, 7], [3, 4], [9, 10]]
    threeCore_assignment = [[0, 1, 2], [6, 7, 8], [3, 4, 5], [9, 10, 11]]
    fourCore_assignment = [[0, 1, 2, 3], [6, 7, 8, 9]]
    eightCore_assignment = [[0, 1, 2, 3, 4, 5, 6, 7]]

    def test_singleCPU_invalid(self):
        # coreLimit, num_of_threads
        self.assertInvalid(2, 5)
        self.assertInvalid(3, 5)
        self.assertInvalid(4, 3)
        self.assertInvalid(8, 2)


# prevent execution of base class as its own test
del TestCpuCoresPerRun
