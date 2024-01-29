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
from benchexec.resources import (
    get_cpu_distribution,
    get_root_level,
    filter_duplicate_hierarchy_levels,
)

sys.dont_write_bytecode = True  # prevent creation of .pyc files


def lrange(start, end):
    return list(range(start, end))


class TestCpuCoresPerRun(unittest.TestCase):
    num_of_packages = None
    num_of_groups = None
    num_of_NUMAs = None
    num_of_L3_regions = None
    num_of_cores = None
    num_of_hyperthreading_siblings = None

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

    def machine(self):
        """Create the necessary parameters of get_cpu_distribution for a specific machine."""

        siblings_of_core = defaultdict(list)
        cores_of_L3cache = defaultdict(list)
        cores_of_NUMA_Region = defaultdict(list)
        cores_of_group = defaultdict(list)
        cores_of_package = defaultdict(list)
        hierarchy_levels = []

        for cpu_nr in range(self.num_of_cores):
            # package
            if self.num_of_packages:
                packageNr = math.trunc(
                    cpu_nr / (self.num_of_cores / self.num_of_packages)
                )
                cores_of_package[packageNr].append(cpu_nr)

            # groups
            if self.num_of_groups:
                groupNr = math.trunc(cpu_nr / (self.num_of_cores / self.num_of_groups))
                cores_of_group[groupNr].append(cpu_nr)

            # numa
            if self.num_of_NUMAs:
                numaNr = math.trunc(cpu_nr / (self.num_of_cores / self.num_of_NUMAs))
                cores_of_NUMA_Region[numaNr].append(cpu_nr)

            # L3
            if self.num_of_L3_regions:
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
            if item:
                hierarchy_levels.append(item)

        # comparator function for number of elements in dictionary
        def compare_hierarchy_by_dict_length(level):
            return len(next(iter(level.values())))

        # sort hierarchy_levels (list of dicts) according to the dicts' corresponding unit sizes
        hierarchy_levels.sort(key=compare_hierarchy_by_dict_length, reverse=False)

        hierarchy_levels.append(get_root_level(hierarchy_levels))

        hierarchy_levels = filter_duplicate_hierarchy_levels(hierarchy_levels)

        return (hierarchy_levels,)

    def mainAssertValid(self, coreLimit, expectedResult, maxThreads=None):
        self.coreLimit = coreLimit
        if expectedResult:
            if maxThreads:
                threadLimit = maxThreads
            else:
                if not self.use_hyperthreading:
                    threadLimit = math.floor(
                        self.num_of_cores
                        / math.ceil(
                            self.coreLimit * self.num_of_hyperthreading_siblings
                        )
                    )
                else:
                    threadLimit = math.floor(
                        self.num_of_cores
                        / (
                            math.ceil(
                                self.coreLimit / self.num_of_hyperthreading_siblings
                            )
                            * self.num_of_hyperthreading_siblings
                        )
                    )
            for num_of_threads in range(threadLimit + 1):
                self.assertValid(
                    self.coreLimit, num_of_threads, expectedResult[:num_of_threads]
                )

    # expected order in which cores are used for runs with coreLimit==1/2/3/4/8, used by the following tests
    # these fields should be filled in by subclasses to activate the corresponding tests
    # (same format as the expected return value by _get_cpu_cores_per_run)
    oneCore_assignment = None
    twoCore_assignment = None
    threeCore_assignment = None
    fourCore_assignment = None
    eightCore_assignment = None
    use_hyperthreading = True

    def test_oneCorePerRun(self):
        # test all possible numOfThread values for runs with one core
        self.mainAssertValid(1, self.oneCore_assignment)

    def test_twoCoresPerRun(self):
        # test all possible numOfThread values for runs with two cores
        self.mainAssertValid(2, self.twoCore_assignment)

    def test_threeCoresPerRun(self):
        # test all possible numOfThread values for runs with three cores
        self.mainAssertValid(3, self.threeCore_assignment)

    def test_fourCoresPerRun(self):
        # test all possible numOfThread values for runs with four cores
        self.mainAssertValid(4, self.fourCore_assignment)

    def test_eightCoresPerRun(self):
        # test all possible numOfThread values for runs with eight cores
        self.mainAssertValid(8, self.eightCore_assignment)


class TestCpuCoresPerRun_singleCPU(TestCpuCoresPerRun):
    num_of_packages = 1
    num_of_cores = 8
    num_of_hyperthreading_siblings = 1
    use_hyperthreading = False

    oneCore_assignment = [[x] for x in range(8)]
    twoCore_assignment = [[0, 1], [2, 3], [4, 5], [6, 7]]
    threeCore_assignment = [[0, 1, 2], [3, 4, 5]]
    fourCore_assignment = [[0, 1, 2, 3], [4, 5, 6, 7]]
    eightCore_assignment = [list(range(8))]

    def test_singleCPU_invalid(self):
        self.assertInvalid(2, 5)
        self.assertInvalid(5, 2)
        self.assertInvalid(3, 3)


class TestCpuCoresPerRun_singleCPU_HT(TestCpuCoresPerRun_singleCPU):
    num_of_cores = 16
    num_of_hyperthreading_siblings = 2
    use_hyperthreading = False

    # 0(1)  2(3)    4(5)    6(7)
    oneCore_assignment = [[x] for x in range(0, 16, 2)]
    twoCore_assignment = [[0, 2], [4, 6], [8, 10], [12, 14]]
    threeCore_assignment = [[0, 2, 4], [6, 8, 10]]
    fourCore_assignment = [[0, 2, 4, 6], [8, 10, 12, 14]]
    eightCore_assignment = [list(range(0, 16, 2))]

    """def test_halfPhysicalCore(self):
        # Can now run if we have only half of one physical core
        self.assertRaises(
            SystemExit,
            get_cpu_distribution,
            1,
            1,
            True,
            {
                0: VirtualCore(0, [0, 0]),
                1: VirtualCore(1, [0, 0]),
            },
            {0: [0, 1]},
            [
                {0: [0, 1]},
                {0: [0, 1]},
            ],
        )"""


class TestCpuCoresPerRun_dualCPU_HT(TestCpuCoresPerRun):
    num_of_packages = 2
    num_of_cores = 32
    num_of_hyperthreading_siblings = 2
    use_hyperthreading = True

    oneCore_assignment = [
        [x]
        for x in [
            0,
            16,
            2,
            18,
            4,
            20,
            6,
            22,
            8,
            24,
            10,
            26,
            12,
            28,
            14,
            30,
        ]
    ]

    twoCore_assignment = [
        [0, 1],
        [16, 17],
        [2, 3],
        [18, 19],
        [4, 5],
        [20, 21],
        [6, 7],
        [22, 23],
        [8, 9],
        [24, 25],
        [10, 11],
        [26, 27],
        [12, 13],
        [28, 29],
        [14, 15],
        [30, 31],
    ]

    # Note: the core assignment here is non-uniform, the last two threads are spread over three physical cores
    # Currently, the assignment algorithm cannot do better for odd coreLimits,
    # but this affects only cases where physical cores are split between runs, which is not recommended anyway.
    threeCore_assignment = [
        [0, 1, 2],
        [16, 17, 18],
        [4, 5, 6],
        [20, 21, 22],
        [8, 9, 10],
        [24, 25, 26],
        [12, 13, 14],
        [28, 29, 30],
    ]

    fourCore_assignment = [
        [0, 1, 2, 3],
        [16, 17, 18, 19],
        [4, 5, 6, 7],
        [20, 21, 22, 23],
        [8, 9, 10, 11],
        [24, 25, 26, 27],
        [12, 13, 14, 15],
        [28, 29, 30, 31],
    ]

    eightCore_assignment = [
        [0, 1, 2, 3, 4, 5, 6, 7],
        [16, 17, 18, 19, 20, 21, 22, 23],
        [8, 9, 10, 11, 12, 13, 14, 15],
        [24, 25, 26, 27, 28, 29, 30, 31],
    ]

    def test_dualCPU_HT(self):
        self.assertValid(16, 2, [lrange(0, 16), lrange(16, 32)])

    def test_dualCPU_HT_invalid(self):
        self.assertInvalid(2, 17)
        self.assertInvalid(17, 2)
        self.assertInvalid(4, 9)
        self.assertInvalid(9, 4)
        self.assertInvalid(8, 5)
        self.assertInvalid(5, 8)


class TestCpuCoresPerRun_threeCPU(TestCpuCoresPerRun):
    num_of_packages = 3
    num_of_cores = 15
    num_of_hyperthreading_siblings = 1
    use_hyperthreading = False

    oneCore_assignment = [
        [x] for x in [0, 5, 10, 1, 6, 11, 2, 7, 12, 3, 8, 13, 4, 9, 14]
    ]
    twoCore_assignment = [
        [0, 1],
        [5, 6],
        [10, 11],
        [2, 3],
        [7, 8],
        [12, 13],
    ]
    threeCore_assignment = [[0, 1, 2], [5, 6, 7], [10, 11, 12]]
    fourCore_assignment = [[0, 1, 2, 3], [5, 6, 7, 8], [10, 11, 12, 13]]
    eightCore_assignment = [[0, 1, 2, 3, 4, 5, 6, 7]]

    def test_twoCoresPerRun(self):
        # Overwritten because the maximum is only 6
        self.mainAssertValid(2, self.twoCore_assignment, 6)

    def test_threeCoresPerRun(self):
        # Overwritten because the maximum is only 3
        self.mainAssertValid(3, self.threeCore_assignment, 3)

    def test_threeCPU_invalid(self):
        self.assertInvalid(6, 2)


class TestCpuCoresPerRun_threeCPU_HT(TestCpuCoresPerRun):
    num_of_packages = 3
    num_of_cores = 30
    num_of_hyperthreading_siblings = 2
    use_hyperthreading = True

    oneCore_assignment = [
        [x] for x in [0, 10, 20, 2, 12, 22, 4, 14, 24, 6, 16, 26, 8, 18, 28]
    ]
    twoCore_assignment = [
        [0, 1],
        [10, 11],
        [20, 21],
        [2, 3],
        [12, 13],
        [22, 23],
        [4, 5],
        [14, 15],
        [24, 25],
        [6, 7],
        [16, 17],
        [26, 27],
        [8, 9],
        [18, 19],
        [28, 29],
    ]
    threeCore_assignment = [
        [0, 1, 2],
        [10, 11, 12],
        [20, 21, 22],
        [4, 5, 6],
        [14, 15, 16],
        [24, 25, 26],
    ]
    fourCore_assignment = [
        [0, 1, 2, 3],
        [10, 11, 12, 13],
        [20, 21, 22, 23],
        [4, 5, 6, 7],
        [14, 15, 16, 17],
        [24, 25, 26, 27],
    ]
    eightCore_assignment = [
        [0, 1, 2, 3, 4, 5, 6, 7],
        [10, 11, 12, 13, 14, 15, 16, 17],
        [20, 21, 22, 23, 24, 25, 26, 27],
    ]

    def test_threeCoresPerRun(self):
        # Overwritten because the maximum is only 6
        self.mainAssertValid(3, self.threeCore_assignment, 6)

    def test_fourCoresPerRun(self):
        # Overwritten because the maximum is only 6
        self.mainAssertValid(3, self.threeCore_assignment, 6)

    def test_threeCPU_HT_invalid(self):
        self.assertInvalid(11, 2)

    def test_threeCPU_HT_noncontiguousId(self):
        """
        3 CPUs with one core (plus HT) and non-contiguous core and package numbers.
        This may happen on systems with administrative core restrictions,
        because the ordering of core and package numbers is not always consistent.
        """
        result = get_cpu_distribution(
            2,
            3,
            True,
            [
                {0: [0, 1], 2: [2, 3], 3: [6, 7]},
                {0: [0, 1, 2, 3, 6, 7]},
            ],
        )
        self.assertEqual(
            [[0, 1], [2, 3], [6, 7]],
            result,
            "Incorrect result for 2 cores and 3 threads.",
        )


class TestCpuCoresPerRun_quadCPU_HT(TestCpuCoresPerRun):
    num_of_packages = 4
    num_of_cores = 64
    num_of_hyperthreading_siblings = 2
    use_hyperthreading = True

    def test_quadCPU_HT(self):
        self.assertValid(
            16,
            4,
            [
                lrange(0, 16),
                lrange(16, 32),
                lrange(32, 48),
                lrange(48, 64),
            ],
        )

        # Just test that no exception occurs
        # Commented out tests are not longer possible
        # self.assertValid(1, 64) - we do not divide HT siblings
        self.assertValid(64, 1)
        self.assertValid(2, 32)
        self.assertValid(32, 2)
        # self.assertValid(3, 20) - we do not divide HT siblings: 4*20 = 80
        self.assertValid(16, 3)
        self.assertValid(4, 16)
        self.assertValid(16, 4)
        # self.assertValid(5, 12) - we do not divide HT siblings: 6*12 =72
        self.assertValid(8, 8)

    def test_quadCPU_HT_invalid(self):
        self.assertInvalid(2, 33)
        self.assertInvalid(33, 2)
        self.assertInvalid(3, 21)
        self.assertInvalid(17, 3)
        self.assertInvalid(4, 17)
        self.assertInvalid(17, 4)
        self.assertInvalid(5, 13)
        self.assertInvalid(9, 5)
        self.assertInvalid(6, 9)
        self.assertInvalid(9, 6)
        self.assertInvalid(7, 9)
        self.assertInvalid(9, 7)
        self.assertInvalid(8, 9)
        self.assertInvalid(9, 8)

        self.assertInvalid(9, 5)
        self.assertInvalid(6, 9)
        self.assertInvalid(10, 5)
        self.assertInvalid(6, 10)
        self.assertInvalid(11, 5)
        self.assertInvalid(6, 11)
        self.assertInvalid(12, 5)
        self.assertInvalid(6, 12)
        self.assertInvalid(13, 5)
        self.assertInvalid(5, 13)
        self.assertInvalid(14, 5)
        self.assertInvalid(5, 14)
        self.assertInvalid(15, 5)
        self.assertInvalid(5, 15)
        self.assertInvalid(16, 5)
        self.assertInvalid(5, 16)


class TestCpuCoresPerRun_singleCPU_no_ht(TestCpuCoresPerRun):
    num_of_packages = 1
    num_of_cores = 8
    num_of_hyperthreading_siblings = 2
    use_hyperthreading = False

    oneCore_assignment = [[x] for x in [0, 2, 4, 6]]
    twoCore_assignment = [[0, 2], [4, 6]]
    threeCore_assignment = [[0, 2, 4]]
    fourCore_assignment = [[0, 2, 4, 6]]

    def test_singleCPU_no_ht_invalid(self):
        self.assertInvalid(1, 5)
        self.assertInvalid(2, 3)
        self.assertInvalid(3, 2)
        self.assertInvalid(4, 2)
        self.assertInvalid(8, 1)


class TestCpuCoresPerRun_dualCPU_no_ht(TestCpuCoresPerRun):
    num_of_packages = 2
    num_of_cores = 16
    num_of_hyperthreading_siblings = 2
    use_hyperthreading = False

    oneCore_assignment = [[0], [8], [2], [10], [4], [12], [6], [14]]
    twoCore_assignment = [[0, 2], [8, 10], [4, 6], [12, 14]]
    threeCore_assignment = [[0, 2, 4], [8, 10, 12]]
    fourCore_assignment = [[0, 2, 4, 6], [8, 10, 12, 14]]
    eightCore_assignment = [[0, 2, 4, 6, 8, 10, 12, 14]]

    def test_dualCPU_no_ht_invalid(self):
        self.assertInvalid(1, 9)
        self.assertInvalid(1, 10)
        self.assertInvalid(2, 5)
        self.assertInvalid(2, 6)
        self.assertInvalid(3, 3)
        self.assertInvalid(3, 4)
        self.assertInvalid(4, 3)
        self.assertInvalid(4, 4)
        self.assertInvalid(8, 2)
        self.assertInvalid(8, 3)


class TestCpuCoresPerRun_threeCPU_no_ht(TestCpuCoresPerRun):
    num_of_packages = 3
    num_of_cores = 18
    num_of_hyperthreading_siblings = 2
    use_hyperthreading = False

    oneCore_assignment = [[x] for x in [0, 6, 12, 2, 8, 14, 4, 10, 16]]
    twoCore_assignment = [[0, 2], [6, 8], [12, 14]]
    threeCore_assignment = [[0, 2, 4], [6, 8, 10], [12, 14, 16]]
    fourCore_assignment = [[0, 2, 4, 6]]
    eightCore_assignment = [[0, 2, 4, 6, 8, 10, 12, 14]]

    def test_threeCPU_no_ht_invalid(self):
        self.assertInvalid(1, 10)
        self.assertInvalid(2, 4)
        self.assertInvalid(3, 4)
        self.assertInvalid(4, 2)
        self.assertInvalid(8, 2)

    def test_twoCoresPerRun(self):
        # Overwritten because the maximum is only 3
        self.mainAssertValid(2, self.twoCore_assignment, 3)

    def test_fourCoresPerRun(self):
        # Overwritten because the maximum is only 3
        self.mainAssertValid(4, self.fourCore_assignment, 1)


class TestCpuCoresPerRun_quadCPU_no_ht(TestCpuCoresPerRun):
    num_of_packages = 4
    num_of_cores = 32
    num_of_hyperthreading_siblings = 2
    use_hyperthreading = False

    oneCore_assignment = [
        [x] for x in [0, 8, 16, 24, 2, 10, 18, 26, 4, 12, 20, 28, 6, 14, 22, 30]
    ]
    twoCore_assignment = [
        [0, 2],
        [8, 10],
        [16, 18],
        [24, 26],
        [4, 6],
        [12, 14],
        [20, 22],
        [28, 30],
    ]
    threeCore_assignment = [[0, 2, 4], [8, 10, 12], [16, 18, 20], [24, 26, 28]]
    fourCore_assignment = [
        [0, 2, 4, 6],
        [8, 10, 12, 14],
        [16, 18, 20, 22],
        [24, 26, 28, 30],
    ]
    eightCore_assignment = [
        [0, 2, 4, 6, 8, 10, 12, 14],
        [16, 18, 20, 22, 24, 26, 28, 30],
    ]

    def test_threeCoresPerRun(self):
        # Overwritten because the maximum is only 6
        self.mainAssertValid(3, self.threeCore_assignment, 4)

    def test_quadCPU_no_ht_invalid(self):
        self.assertInvalid(1, 17)
        self.assertInvalid(2, 9)
        self.assertInvalid(3, 5)
        self.assertInvalid(4, 5)
        self.assertInvalid(8, 3)

    def test_quadCPU_no_ht_valid(self):
        self.assertValid(5, 2, [[0, 2, 4, 6, 8], [16, 18, 20, 22, 24]])
        self.assertInvalid(5, 3)
        self.assertValid(6, 2, [[0, 2, 4, 6, 8, 10], [16, 18, 20, 22, 24, 26]])
        self.assertInvalid(6, 3)


class Test_Topology_P1_NUMA2_L8_C16_F(TestCpuCoresPerRun):
    num_of_packages = 1
    num_of_NUMAs = 2
    num_of_L3_regions = 8
    num_of_cores = 16
    num_of_hyperthreading_siblings = 2
    use_hyperthreading = False

    """
    x : symbolizes a unit (package, NUMA, L3)
    - : visualizes that a core is there, but it is not available because
        use_hyperthreading is set to False
    int: core id
                         x

            x                       x

    x   x       x   x       x   x      x    x

    0-  2-     4-   6-     8-   10-   12-  14-
    """
    # expected results for different coreLimits
    oneCore_assignment = [[x] for x in [0, 8, 2, 10, 4, 12, 6, 14]]
    twoCore_assignment = [[0, 2], [8, 10], [4, 6], [12, 14]]
    threeCore_assignment = [[0, 2, 4], [8, 10, 12]]
    fourCore_assignment = [[0, 2, 4, 6], [8, 10, 12, 14]]
    fiveCore_assignment = [[0, 2, 4, 6, 8]]
    eightCore_assignment = [[0, 2, 4, 6, 8, 10, 12, 14]]

    def test_fiveCoresPerRun(self):
        self.mainAssertValid(5, self.fiveCore_assignment)

    def test_invalid(self):
        # coreLimit, num_of_threads
        self.assertInvalid(2, 5)
        self.assertInvalid(5, 2)
        self.assertInvalid(3, 3)


class Test_Topology_P1_NUMA2_L8_C16_T(TestCpuCoresPerRun):
    num_of_packages = 1
    num_of_NUMAs = 2
    num_of_L3_regions = 8
    num_of_cores = 16
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

    def test_invalid(self):
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
    threeCore_assignment = [[0, 2, 4]]
    fourCore_assignment = [[0, 2, 4, 6]]

    def test_threeCoresPerRun(self):
        self.mainAssertValid(3, self.threeCore_assignment, 1)

    def test_invalid(self):
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
    fiveCore_assignment = [[0, 1, 2, 3, 4]]
    eightCore_assignment = [[0, 1, 2, 3, 4, 5, 6, 7]]

    def test_fiveCoresPerRun(self):
        self.mainAssertValid(5, self.fiveCore_assignment, 1)

    def test_invalid(self):
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

    def test_invalid(self):
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

    def test_invalid(self):
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

    def test_invalid(self):
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

    def test_invalid(self):
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

    def test_invalid(self):
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

    def test_invalid(self):
        # coreLimit, num_of_threads
        self.assertInvalid(2, 5)
        self.assertInvalid(3, 5)
        self.assertInvalid(4, 3)
        self.assertInvalid(8, 2)


class Test_Topology_P2_G2_NUMA8_L16_C256_T(TestCpuCoresPerRun):
    num_of_packages = 2
    num_of_groups = 2
    num_of_NUMAs = 8
    num_of_L3_regions = 16
    num_of_cores = 256
    num_of_hyperthreading_siblings = 2
    use_hyperthreading = True

    # fmt: off

    # expected results for different coreLimits
    oneCore_assignment = [[x] for x in [
        0, 128, 32, 160, 64, 192, 96, 224,
        16, 144, 48, 176, 80, 208, 112, 240,
        2, 130, 34, 162, 66, 194, 98, 226,
        18, 146, 50, 178, 82, 210, 114, 242,
        4, 132, 36, 164, 68, 196, 100, 228,
        20, 148, 52, 180, 84, 212, 116, 244,
        6, 134, 38, 166, 70, 198, 102, 230,
        22, 150, 54, 182, 86, 214, 118, 246,
        8, 136, 40, 168, 72, 200, 104, 232,
        24, 152, 56, 184, 88, 216, 120, 248,
        10, 138, 42, 170, 74, 202, 106, 234,
        26, 154, 58, 186, 90, 218, 122, 250,
        12, 140, 44, 172, 76, 204, 108, 236,
        28, 156, 60, 188, 92, 220, 124, 252,
        14, 142, 46, 174, 78, 206, 110, 238,
        30, 158, 62, 190, 94, 222, 126, 254
    ]]
    twoCore_assignment = [
        [0, 1], [128, 129], [32, 33], [160, 161], [64, 65], [192, 193], [96, 97], [224, 225],
        [16, 17], [144, 145], [48, 49], [176, 177], [80, 81], [208, 209], [112, 113], [240, 241],
        [2, 3], [130, 131], [34, 35], [162, 163], [66, 67], [194, 195], [98, 99], [226, 227],
        [18, 19], [146, 147], [50, 51], [178, 179], [82, 83], [210, 211], [114, 115], [242, 243],
        [4, 5], [132, 133], [36, 37], [164, 165], [68, 69], [196, 197], [100, 101], [228, 229],
        [20, 21], [148, 149], [52, 53], [180, 181], [84, 85], [212, 213], [116, 117], [244, 245],
        [6, 7], [134, 135], [38, 39], [166, 167], [70, 71], [198, 199], [102, 103], [230, 231],
        [22, 23], [150, 151], [54, 55], [182, 183], [86, 87], [214, 215], [118, 119], [246, 247],
        [8, 9], [136, 137], [40, 41], [168, 169], [72, 73], [200, 201], [104, 105], [232, 233],
        [24, 25], [152, 153], [56, 57], [184, 185], [88, 89], [216, 217], [120, 121], [248, 249],
        [10, 11], [138, 139], [42, 43], [170, 171], [74, 75], [202, 203], [106, 107], [234, 235],
        [26, 27], [154, 155], [58, 59], [186, 187], [90, 91], [218, 219], [122, 123], [250, 251],
        [12, 13], [140, 141], [44, 45], [172, 173], [76, 77], [204, 205], [108, 109], [236, 237],
        [28, 29], [156, 157], [60, 61], [188, 189], [92, 93], [220, 221], [124, 125], [252, 253],
        [14, 15], [142, 143], [46, 47], [174, 175], [78, 79], [206, 207], [110, 111], [238, 239],
        [30, 31], [158, 159], [62, 63], [190, 191], [94, 95], [222, 223], [126, 127], [254, 255]
    ]
    threeCore_assignment = [
        [0, 1, 2], [128, 129, 130], [32, 33, 34], [160, 161, 162], [64, 65, 66], [192, 193, 194], [96, 97, 98], [224, 225, 226],
        [16, 17, 18], [144, 145, 146], [48, 49, 50], [176, 177, 178], [80, 81, 82], [208, 209, 210], [112, 113, 114], [240, 241, 242],
        [4, 5, 6], [132, 133, 134], [36, 37, 38], [164, 165, 166], [68, 69, 70], [196, 197, 198], [100, 101, 102], [228, 229, 230],
        [20, 21, 22], [148, 149, 150], [52, 53, 54], [180, 181, 182], [84, 85, 86], [212, 213, 214], [116, 117, 118], [244, 245, 246],
        [8, 9, 10], [136, 137, 138], [40, 41, 42], [168, 169, 170], [72, 73, 74], [200, 201, 202], [104, 105, 106], [232, 233, 234],
        [24, 25, 26], [152, 153, 154], [56, 57, 58], [184, 185, 186], [88, 89, 90], [216, 217, 218], [120, 121, 122], [248, 249, 250],
        [12, 13, 14], [140, 141, 142], [44, 45, 46], [172, 173, 174], [76, 77, 78], [204, 205, 206], [108, 109, 110], [236, 237, 238],
        [28, 29, 30], [156, 157, 158], [60, 61, 62], [188, 189, 190], [92, 93, 94], [220, 221, 222], [124, 125, 126], [252, 253, 254],
    ]
    fourCore_assignment = [
        [0, 1, 2, 3], [128, 129, 130, 131], [32, 33, 34, 35], [160, 161, 162, 163], [64, 65, 66, 67], [192, 193, 194, 195], [96, 97, 98, 99], [224, 225, 226, 227],
        [16, 17, 18, 19], [144, 145, 146, 147], [48, 49, 50, 51], [176, 177, 178, 179], [80, 81, 82, 83], [208, 209, 210, 211], [112, 113, 114, 115], [240, 241, 242, 243],
        [4, 5, 6, 7], [132, 133, 134, 135], [36, 37, 38, 39], [164, 165, 166, 167], [68, 69, 70, 71], [196, 197, 198, 199], [100, 101, 102, 103], [228, 229, 230, 231],
        [20, 21, 22, 23], [148, 149, 150, 151], [52, 53, 54, 55], [180, 181, 182, 183], [84, 85, 86, 87], [212, 213, 214, 215], [116, 117, 118, 119], [244, 245, 246, 247],
        [8, 9, 10, 11], [136, 137, 138, 139], [40, 41, 42, 43], [168, 169, 170, 171], [72, 73, 74, 75], [200, 201, 202, 203], [104, 105, 106, 107], [232, 233, 234, 235],
        [24, 25, 26, 27], [152, 153, 154, 155], [56, 57, 58, 59], [184, 185, 186, 187], [88, 89, 90, 91], [216, 217, 218, 219], [120, 121, 122, 123], [248, 249, 250, 251],
        [12, 13, 14, 15], [140, 141, 142, 143], [44, 45, 46, 47], [172, 173, 174, 175], [76, 77, 78, 79], [204, 205, 206, 207], [108, 109, 110, 111], [236, 237, 238, 239],
        [28, 29, 30, 31], [156, 157, 158, 159], [60, 61, 62, 63], [188, 189, 190, 191], [92, 93, 94, 95], [220, 221, 222, 223], [124, 125, 126, 127], [252, 253, 254, 255],
    ]
    eightCore_assignment = [
        [0, 1, 2, 3, 4, 5, 6, 7], [128, 129, 130, 131, 132, 133, 134, 135], [32, 33, 34, 35, 36, 37, 38, 39], [160, 161, 162, 163, 164, 165, 166, 167], [64, 65, 66, 67, 68, 69, 70, 71], [192, 193, 194, 195, 196, 197, 198, 199], [96, 97, 98, 99, 100, 101, 102, 103], [224, 225, 226, 227, 228, 229, 230, 231],
        [16, 17, 18, 19, 20, 21, 22, 23], [144, 145, 146, 147, 148, 149, 150, 151], [48, 49, 50, 51, 52, 53, 54, 55], [176, 177, 178, 179, 180, 181, 182, 183], [80, 81, 82, 83, 84, 85, 86, 87], [208, 209, 210, 211, 212, 213, 214, 215], [112, 113, 114, 115, 116, 117, 118, 119], [240, 241, 242, 243, 244, 245, 246, 247],
        [8, 9, 10, 11, 12, 13, 14, 15], [136, 137, 138, 139, 140, 141, 142, 143], [40, 41, 42, 43, 44, 45, 46, 47], [168, 169, 170, 171, 172, 173, 174, 175], [72, 73, 74, 75, 76, 77, 78, 79], [200, 201, 202, 203, 204, 205, 206, 207], [104, 105, 106, 107, 108, 109, 110, 111], [232, 233, 234, 235, 236, 237, 238, 239],
        [24, 25, 26, 27, 28, 29, 30, 31], [152, 153, 154, 155, 156, 157, 158, 159], [56, 57, 58, 59, 60, 61, 62, 63], [184, 185, 186, 187, 188, 189, 190, 191], [88, 89, 90, 91, 92, 93, 94, 95], [216, 217, 218, 219, 220, 221, 222, 223], [120, 121, 122, 123, 124, 125, 126, 127], [248, 249, 250, 251, 252, 253, 254, 255],
    ]

    # fmt: on


# prevent execution of base class as its own test
del TestCpuCoresPerRun
