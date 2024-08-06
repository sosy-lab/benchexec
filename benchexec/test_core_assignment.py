# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import itertools
import unittest
import math

from benchexec.resources import _get_cpu_cores_per_run0


def lrange(start, end):
    return list(range(start, end))


class TestCpuCoresPerRun(unittest.TestCase):

    def assertValid(self, coreLimit, num_of_threads, expectedResult=None):
        result = _get_cpu_cores_per_run0(
            coreLimit, num_of_threads, self.use_ht, *self.machine()
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
            _get_cpu_cores_per_run0,
            coreLimit,
            num_of_threads,
            self.use_ht,
            *self.machine(),
        )

    def machine(self):
        """Create the necessary parameters of _get_cpu_cores_per_run0 for a specific machine."""
        core_count = self.cpus * self.cores
        allCpus = range(core_count)
        cores_of_package = {}
        ht_spread = core_count // 2
        for package in range(self.cpus):
            start = package * self.cores // (2 if self.ht else 1)
            end = (package + 1) * self.cores // (2 if self.ht else 1)
            cores_of_package[package] = lrange(start, end)
            if self.ht:
                cores_of_package[package].extend(
                    range(start + ht_spread, end + ht_spread)
                )
        siblings_of_core = {}
        for core in allCpus:
            siblings_of_core[core] = [core]
        if self.ht:
            for core in allCpus:
                siblings_of_core[core].append((core + ht_spread) % core_count)
                siblings_of_core[core].sort()
        return allCpus, cores_of_package, siblings_of_core

    def test_singleThread(self):
        # test all possible coreLimits for a single thread
        core_count = self.cpus * self.cores
        if self.ht:
            # Creates list alternating between real core and hyper-threading core
            singleThread_assignment = list(
                itertools.chain(
                    *zip(range(core_count // 2), range(core_count // 2, core_count))
                )
            )
        else:
            singleThread_assignment = lrange(0, core_count)
        if not self.use_ht and self.ht:
            core_count = (self.cpus * self.cores) // 2
            singleThread_assignment = lrange(0, core_count)

        for coreLimit in range(1, core_count + 1):
            self.assertValid(
                coreLimit, 1, [sorted(singleThread_assignment[:coreLimit])]
            )
        self.assertInvalid(core_count + 1, 1)

    # expected order in which cores are used for runs with coreLimit==1/2/3/4/8, used by the following tests
    # these fields should be filled in by subclasses to activate the corresponding tests
    # (same format as the expected return value by _get_cpu_cores_per_run)
    oneCore_assignment = None
    twoCore_assignment = None
    threeCore_assignment = None
    fourCore_assignment = None
    eightCore_assignment = None
    use_ht = True

    def test_oneCorePerRun(self):
        # test all possible numOfThread values for runs with one core
        maxThreads = self.cpus * self.cores
        if not self.use_ht and self.ht:
            maxThreads = (self.cpus * self.cores) // 2
        self.assertInvalid(1, maxThreads + 1)
        if not self.oneCore_assignment:
            self.skipTest("Need result specified")
        for num_of_threads in range(1, maxThreads + 1):
            self.assertValid(
                1, num_of_threads, self.oneCore_assignment[:num_of_threads]
            )

    def test_twoCoresPerRun(self):
        # test all possible numOfThread values for runs with two cores
        maxThreads = self.cpus * (self.cores // 2)
        if not self.use_ht and self.ht:
            maxThreads = self.cpus * (self.cores // 4)
            if maxThreads == 0:
                # Test for runs that are split over cpus
                cpus_per_run = int(math.ceil(2 / (self.cores // 2)))
                maxThreads = self.cpus // cpus_per_run
        self.assertInvalid(2, maxThreads + 1)
        if not self.twoCore_assignment:
            self.skipTest("Need result specified")
        for num_of_threads in range(1, maxThreads + 1):
            self.assertValid(
                2, num_of_threads, self.twoCore_assignment[:num_of_threads]
            )

    def test_threeCoresPerRun(self):
        # test all possible numOfThread values for runs with three cores
        maxThreads = self.cpus * (self.cores // 3)
        if not self.use_ht and self.ht:
            maxThreads = self.cpus * (self.cores // 6)
            if maxThreads == 0:
                # Test for runs that are split over cpus
                cpus_per_run = int(math.ceil(3 / (self.cores // 2)))
                maxThreads = self.cpus // cpus_per_run

        self.assertInvalid(3, maxThreads + 1)
        if not self.threeCore_assignment:
            self.skipTest("Need result specified")
        for num_of_threads in range(1, maxThreads + 1):
            self.assertValid(
                3, num_of_threads, self.threeCore_assignment[:num_of_threads]
            )

    def test_fourCoresPerRun(self):
        # test all possible numOfThread values for runs with four cores
        maxThreads = self.cpus * (self.cores // 4)
        if not self.use_ht and self.ht:
            maxThreads = self.cpus * (self.cores // 8)
            if maxThreads == 0:
                # Test for runs that are split over cpus
                cpus_per_run = int(math.ceil(4 / (self.cores // 2)))
                maxThreads = self.cpus // cpus_per_run

        self.assertInvalid(4, maxThreads + 1)
        if not self.fourCore_assignment:
            self.skipTest("Need result specified")
        for num_of_threads in range(1, maxThreads + 1):
            self.assertValid(
                4, num_of_threads, self.fourCore_assignment[:num_of_threads]
            )

    def test_eightCoresPerRun(self):
        # test all possible numOfThread values for runs with eight cores
        maxThreads = self.cpus * (self.cores // 8)
        if not self.use_ht and self.ht:
            maxThreads = (self.cpus * self.cores) // 16
            if maxThreads == 0:
                # Test for runs that are split over cpus
                cpus_per_run = int(math.ceil(8 / (self.cores // 2)))
                maxThreads = self.cpus // cpus_per_run
        if not maxThreads:
            self.skipTest(
                "Testing for runs that need to be split across CPUs is not implemented"
            )
        self.assertInvalid(8, maxThreads + 1)
        if not self.eightCore_assignment:
            self.skipTest("Need result specified")
        for num_of_threads in range(1, maxThreads + 1):
            self.assertValid(
                8, num_of_threads, self.eightCore_assignment[:num_of_threads]
            )


class TestCpuCoresPerRun_singleCPU(TestCpuCoresPerRun):
    cpus = 1
    cores = 8
    ht = False

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
    ht = True

    twoCore_assignment = [[0, 4], [1, 5], [2, 6], [3, 7]]
    threeCore_assignment = [[0, 1, 4], [2, 3, 6]]
    fourCore_assignment = [[0, 1, 4, 5], [2, 3, 6, 7]]

    def test_halfPhysicalCore(self):
        # Cannot run if we have only half of one physical core
        self.assertRaises(
            SystemExit,
            _get_cpu_cores_per_run0,
            1,
            1,
            True,
            [0],
            {0: [0, 1]},
            {0: [0, 1]},
        )


class TestCpuCoresPerRun_dualCPU_HT(TestCpuCoresPerRun):
    cpus = 2
    cores = 16
    ht = True

    oneCore_assignment = [
        [x]
        for x in [
            0,
            8,
            1,
            9,
            2,
            10,
            3,
            11,
            4,
            12,
            5,
            13,
            6,
            14,
            7,
            15,
            16,
            24,
            17,
            25,
            18,
            26,
            19,
            27,
            20,
            28,
            21,
            29,
            22,
            30,
            23,
            31,
        ]
    ]

    twoCore_assignment = [
        [0, 16],
        [8, 24],
        [1, 17],
        [9, 25],
        [2, 18],
        [10, 26],
        [3, 19],
        [11, 27],
        [4, 20],
        [12, 28],
        [5, 21],
        [13, 29],
        [6, 22],
        [14, 30],
        [7, 23],
        [15, 31],
    ]

    # Note: the core assignment here is non-uniform, the last two threads are spread over three physical cores
    # Currently, the assignment algorithm cannot do better for odd coreLimits,
    # but this affects only cases where physical cores are split between runs, which is not recommended anyway.
    threeCore_assignment = [
        [0, 1, 16],
        [8, 9, 24],
        [2, 3, 18],
        [10, 11, 26],
        [4, 5, 20],
        [12, 13, 28],
        [6, 7, 22],
        [14, 15, 30],
        [17, 19, 21],
        [25, 27, 29],
    ]

    fourCore_assignment = [
        [0, 1, 16, 17],
        [8, 9, 24, 25],
        [2, 3, 18, 19],
        [10, 11, 26, 27],
        [4, 5, 20, 21],
        [12, 13, 28, 29],
        [6, 7, 22, 23],
        [14, 15, 30, 31],
    ]

    eightCore_assignment = [
        [0, 1, 2, 3, 16, 17, 18, 19],
        [8, 9, 10, 11, 24, 25, 26, 27],
        [4, 5, 6, 7, 20, 21, 22, 23],
        [12, 13, 14, 15, 28, 29, 30, 31],
    ]

    def test_dualCPU_HT(self):
        self.assertValid(
            16, 2, [lrange(0, 8) + lrange(16, 24), lrange(8, 16) + lrange(24, 32)]
        )

    def test_dualCPU_HT_invalid(self):
        self.assertInvalid(2, 17)
        self.assertInvalid(17, 2)
        self.assertInvalid(4, 9)
        self.assertInvalid(9, 4)
        self.assertInvalid(8, 5)
        self.assertInvalid(5, 8)


class TestCpuCoresPerRun_threeCPU(TestCpuCoresPerRun):
    cpus = 3
    cores = 5
    ht = False

    oneCore_assignment = [
        [x] for x in [0, 5, 10, 1, 6, 11, 2, 7, 12, 3, 8, 13, 4, 9, 14]
    ]
    twoCore_assignment = [[0, 1], [5, 6], [10, 11], [2, 3], [7, 8], [12, 13]]
    threeCore_assignment = [[0, 1, 2], [5, 6, 7], [10, 11, 12]]
    fourCore_assignment = [[0, 1, 2, 3], [5, 6, 7, 8], [10, 11, 12, 13]]

    def test_threeCPU_invalid(self):
        self.assertInvalid(6, 2)


class TestCpuCoresPerRun_threeCPU_HT(TestCpuCoresPerRun):
    cpus = 3
    cores = 10
    ht = True

    oneCore_assignment = [
        [x]
        for x in [
            0,
            5,
            10,
            1,
            6,
            11,
            2,
            7,
            12,
            3,
            8,
            13,
            4,
            9,
            14,
            15,
            20,
            25,
            16,
            21,
            26,
            17,
            22,
            27,
            18,
            23,
            28,
            19,
            24,
            29,
        ]
    ]
    twoCore_assignment = [
        [0, 15],
        [5, 20],
        [10, 25],
        [1, 16],
        [6, 21],
        [11, 26],
        [2, 17],
        [7, 22],
        [12, 27],
        [3, 18],
        [8, 23],
        [13, 28],
        [4, 19],
        [9, 24],
        [14, 29],
    ]
    threeCore_assignment = [
        [0, 1, 15],
        [5, 6, 20],
        [10, 11, 25],
        [2, 3, 17],
        [7, 8, 22],
        [12, 13, 27],
        [4, 16, 19],
        [9, 21, 24],
        [14, 26, 29],
    ]
    fourCore_assignment = [
        [0, 1, 15, 16],
        [5, 6, 20, 21],
        [10, 11, 25, 26],
        [2, 3, 17, 18],
        [7, 8, 22, 23],
        [12, 13, 27, 28],
    ]
    eightCore_assignment = [
        [0, 1, 2, 3, 15, 16, 17, 18],
        [5, 6, 7, 8, 20, 21, 22, 23],
        [10, 11, 12, 13, 25, 26, 27, 28],
    ]

    def test_threeCPU_HT_invalid(self):
        self.assertInvalid(11, 2)

    def test_threeCPU_HT_noncontiguousId(self):
        """3 CPUs with one core (plus HT) and non-contiguous core and package numbers.
        This may happen on systems with administrative core restrictions,
        because the ordering of core and package numbers is not always consistent."""
        result = _get_cpu_cores_per_run0(
            2,
            3,
            True,
            [0, 1, 2, 3, 6, 7],
            {0: [0, 1], 2: [2, 3], 3: [6, 7]},
            {0: [0, 1], 1: [0, 1], 2: [2, 3], 3: [2, 3], 6: [6, 7], 7: [6, 7]},
        )
        self.assertEqual(
            [[0, 1], [2, 3], [6, 7]],
            result,
            "Incorrect result for 2 cores and 3 threads.",
        )


class TestCpuCoresPerRun_quadCPU_HT(TestCpuCoresPerRun):
    cpus = 4
    cores = 16
    ht = True

    def test_quadCPU_HT_noncontiguousId(self):
        """4 CPUs with 8 cores (plus HT) and non-contiguous core and package numbers.
        This may happen on systems with administrative core restrictions,
        because the ordering of core and package numbers is not always consistent.
        Furthermore, sibling cores have numbers next to each other (occurs on AMD Opteron machines with shared L1/L2 caches)
        and are not split as far as possible from each other (as it occurs on hyper-threading machines).
        """
        result = _get_cpu_cores_per_run0(
            1,
            8,
            True,
            [0, 1, 8, 9, 16, 17, 24, 25, 32, 33, 40, 41, 48, 49, 56, 57],
            {
                0: [0, 1, 8, 9],
                1: [32, 33, 40, 41],
                2: [48, 49, 56, 57],
                3: [16, 17, 24, 25],
            },
            {
                0: [0, 1],
                1: [0, 1],
                48: [48, 49],
                33: [32, 33],
                32: [32, 33],
                40: [40, 41],
                9: [8, 9],
                16: [16, 17],
                17: [16, 17],
                56: [56, 57],
                57: [56, 57],
                8: [8, 9],
                41: [40, 41],
                24: [24, 25],
                25: [24, 25],
                49: [48, 49],
            },
        )
        self.assertEqual(
            [[0], [32], [48], [16], [8], [40], [56], [24]],
            result,
            "Incorrect result for 1 core and 8 threads.",
        )

    def test_quadCPU_HT(self):
        self.assertValid(
            16,
            4,
            [
                lrange(0, 8) + lrange(32, 40),
                lrange(8, 16) + lrange(40, 48),
                lrange(16, 24) + lrange(48, 56),
                lrange(24, 32) + lrange(56, 64),
            ],
        )

        # Just test that no exception occurs
        self.assertValid(1, 64)
        self.assertValid(64, 1)
        self.assertValid(2, 32)
        self.assertValid(32, 2)
        self.assertValid(3, 20)
        self.assertValid(16, 3)
        self.assertValid(4, 16)
        self.assertValid(16, 4)
        self.assertValid(5, 12)
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
    cpus = 1
    cores = 8
    ht = True
    use_ht = False

    oneCore_assignment = [[x] for x in range(0, 4)]
    twoCore_assignment = [[0, 1], [2, 3]]
    threeCore_assignment = [[0, 1, 2]]
    fourCore_assignment = [[0, 1, 2, 3]]

    def test_singleCPU_no_ht_invalid(self):
        self.assertInvalid(1, 5)
        self.assertInvalid(2, 3)
        self.assertInvalid(3, 2)
        self.assertInvalid(4, 2)
        self.assertInvalid(8, 1)


class TestCpuCoresPerRun_dualCPU_no_ht(TestCpuCoresPerRun):
    cpus = 2
    cores = 8
    ht = True
    use_ht = False

    oneCore_assignment = [[0], [4], [1], [5], [2], [6], [3], [7]]
    twoCore_assignment = [[0, 1], [4, 5], [2, 3], [6, 7]]
    threeCore_assignment = [[0, 1, 2], [4, 5, 6]]
    fourCore_assignment = [[0, 1, 2, 3], [4, 5, 6, 7]]
    eightCore_assignment = [[0, 1, 2, 3, 4, 5, 6, 7]]

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

    def test_dualCPU_noncontiguousID(self):
        results = _get_cpu_cores_per_run0(
            2,
            3,
            False,
            [0, 4, 9, 15, 21, 19, 31, 12, 10, 11, 8, 23, 27, 14, 1, 20],
            {0: [0, 4, 9, 12, 15, 19, 21, 31], 2: [10, 11, 8, 23, 27, 14, 1, 20]},
            {
                0: [0, 4],
                4: [0, 4],
                9: [9, 12],
                12: [9, 12],
                15: [15, 19],
                19: [15, 19],
                21: [21, 31],
                31: [21, 31],
                10: [10, 11],
                11: [10, 11],
                8: [8, 23],
                23: [8, 23],
                27: [27, 14],
                14: [27, 14],
                1: [1, 20],
                20: [1, 20],
            },
        )
        self.assertEqual(
            results,
            [[0, 9], [8, 10], [15, 21]],
            "Incorrect result for 2 cores and 3 threads.",
        )


class TestCpuCoresPerRun_threeCPU_no_ht(TestCpuCoresPerRun):
    cpus = 3
    cores = 6
    ht = True
    use_ht = False

    oneCore_assignment = [[x] for x in [0, 3, 6, 1, 4, 7, 2, 5, 8]]
    twoCore_assignment = [[0, 1], [3, 4], [6, 7]]
    threeCore_assignment = [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
    fourCore_assignment = [[0, 1, 2, 3]]
    eightCore_assignment = [[0, 1, 2, 3, 4, 5, 6, 7]]

    def test_threeCPU_no_ht_invalid(self):
        self.assertInvalid(1, 10)
        self.assertInvalid(2, 4)
        self.assertInvalid(3, 4)
        self.assertInvalid(4, 2)
        self.assertInvalid(8, 2)


class TestCpuCoresPerRun_quadCPU_no_ht(TestCpuCoresPerRun):
    cpus = 4
    cores = 8
    ht = True
    use_ht = False

    oneCore_assignment = [
        [x] for x in [0, 4, 8, 12, 1, 5, 9, 13, 2, 6, 10, 14, 3, 7, 11, 15]
    ]
    twoCore_assignment = [
        [0, 1],
        [4, 5],
        [8, 9],
        [12, 13],
        [2, 3],
        [6, 7],
        [10, 11],
        [14, 15],
    ]
    threeCore_assignment = [[0, 1, 2], [4, 5, 6], [8, 9, 10], [12, 13, 14]]
    fourCore_assignment = [[0, 1, 2, 3], [4, 5, 6, 7], [8, 9, 10, 11], [12, 13, 14, 15]]
    eightCore_assignment = [[0, 1, 2, 3, 4, 5, 6, 7], [8, 9, 10, 11, 12, 13, 14, 15]]

    def test_quadCPU_no_ht_invalid(self):
        self.assertInvalid(1, 17)
        self.assertInvalid(2, 9)
        self.assertInvalid(3, 5)
        self.assertInvalid(4, 5)
        self.assertInvalid(8, 3)

    def test_quadCPU_no_ht_valid(self):
        self.assertValid(5, 2, [[0, 1, 2, 3, 4], [8, 9, 10, 11, 12]])
        self.assertInvalid(5, 3)
        self.assertValid(6, 2, [[0, 1, 2, 3, 4, 5], [8, 9, 10, 11, 12, 13]])
        self.assertInvalid(6, 3)


# prevent execution of base class as its own test
del TestCpuCoresPerRun
