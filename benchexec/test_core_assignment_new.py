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
    filter_duplicate_hierarchy_levels,
)
import pytest

sys.dont_write_bytecode = True  # prevent creation of .pyc files


def expect_assignment(
    number_cores: int, expected_assignment: list, max_threads=None
) -> callable:
    """
    Add a new test case "test_(number_cores)_cores_assignment", which checks if the results match the expected assignment
    The test will automatically be run by pytest

    @param: number_cores            the number of cores for each parallel benchmark execution
    @param: expected_assignment     the expected assignment as a ground truth
    @param: max_threads             the max number of threads which can be used, or None if unlimited
    """

    def class_decorator(c) -> callable:
        def decorator_test_assignment(self):
            self.mainAssertValid(number_cores, expected_assignment, max_threads)

        dynamic_test_name = f"test_{number_cores}_cores_assignment"
        setattr(c, dynamic_test_name, decorator_test_assignment)
        return c

    return class_decorator


def expect_valid(core_and_thread_tupels: list, expected_assignment: list) -> callable:
    """
    Add a new test case "test_(number_cores)_cores_(number_threads)_threads_expected_result", which asserts if a certain
    combination of core limit and thread requirements return the expected result

    @param: core_and_thread_tupels  list of tupels with a max numbers of cores which may be used and required number of threads
    @param: expected_assignment     single expected assignment for all tupels
    """

    def class_decorator(c) -> callable:
        for number_cores, number_threads in core_and_thread_tupels:

            def decorator_test_invalid(self):
                self.assertValid(number_cores, number_threads, expected_assignment)

            dynamic_test_name = (
                f"test_{number_cores}_cores_{number_threads}_threads_expected_result"
            )
            setattr(c, dynamic_test_name, decorator_test_invalid)
        return c

    return class_decorator


def expect_invalid(core_and_thread_tupels: list) -> callable:
    """
    Add a new test case "test_(number_cores)_cores_(number_threads)_threads_invalid", which checks if an exception is raised due to
    impossibility of an assignment

    @param: core_and_thread_tupels  list of tupels with invalid numbers of cores and threads
    """

    def class_decorator(c) -> callable:
        for number_cores, number_threads in core_and_thread_tupels:

            def decorator_test_invalid(self):
                with pytest.raises(SystemExit):
                    get_cpu_distribution(
                        number_cores,
                        number_threads,
                        self.use_hyperthreading,
                        *self.machine(),
                    )

            dynamic_test_name = (
                f"test_{number_cores}_cores_{number_threads}_threads_invalid"
            )
            setattr(c, dynamic_test_name, decorator_test_invalid)
        return c

    return class_decorator


def lrange(start, end):
    return list(range(start, end))


class TestCpuCoresPerRun(unittest.TestCase):
    num_of_cores = None

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

    machine_definition = None

    def test_assert_refactor_translation_identical(self):
        self.machine()

    def machine(self):
        """Create the necessary parameters of get_cpu_distribution for a specific machine."""

        layer_definition, _virtual_cores_per_core = self.machine_definition
        self.num_of_cores = layer_definition[0] * _virtual_cores_per_core

        layers = []

        for _i in range(len(layer_definition)):
            _layer = defaultdict(list)
            for cpu_nr in range(self.num_of_cores):
                print("doing: " + str(_i) + " for " + str(cpu_nr))
                layer_number = math.trunc(
                    cpu_nr / (self.num_of_cores / layer_definition[_i])
                )
                # v again, it shouldn't matter in the end, but let's keep consistent with the current implementation to keep the
                # tests consistent: hyperthreading "cores" get the id of their real core
                if _i == 0:
                    layer_number = layer_number * _virtual_cores_per_core
                    layer_number -= layer_number % _virtual_cores_per_core
                # ^ we can probably get rid of this piece of code in the end, TODO
                _layer[layer_number] = _layer.get(layer_number, [])
                _layer[layer_number].append(cpu_nr)
            layers.append(_layer)

        # all cores as the final layer
        layers.append({0: list(range(self.num_of_cores))})

        layers = filter_duplicate_hierarchy_levels(layers)

        return (layers,)

    def mainAssertValid(self, coreLimit, expectedResult, maxThreads=None):
        _layer_definition, _virtual_cores_per_core = self.machine_definition
        self.num_of_cores = _layer_definition[0] * _virtual_cores_per_core
        self.coreLimit = coreLimit
        if expectedResult:
            if maxThreads:
                threadLimit = maxThreads
            else:
                if not self.use_hyperthreading:
                    threadLimit = math.floor(
                        self.num_of_cores
                        / math.ceil(self.coreLimit * _virtual_cores_per_core)
                    )
                else:
                    threadLimit = math.floor(
                        self.num_of_cores
                        / (
                            math.ceil(self.coreLimit / _virtual_cores_per_core)
                            * _virtual_cores_per_core
                        )
                    )
            for num_of_threads in range(threadLimit + 1):
                self.assertValid(
                    self.coreLimit, num_of_threads, expectedResult[:num_of_threads]
                )

    use_hyperthreading = True


@expect_assignment(1, [[x] for x in range(8)])
@expect_assignment(2, [[0, 1], [2, 3], [4, 5], [6, 7]])
@expect_assignment(3, [[0, 1, 2], [3, 4, 5]])
@expect_assignment(4, [[0, 1, 2, 3], [4, 5, 6, 7]])
@expect_assignment(8, [list(range(8))])
@expect_invalid([(2, 5), (5, 2), (3, 3)])
class TestCpuCoresPerRun_singleCPU(TestCpuCoresPerRun):
    use_hyperthreading = False
    machine_definition = ([8, 1], 1)


@expect_assignment(1, [[x] for x in range(0, 16, 2)])
@expect_assignment(2, [[0, 2], [4, 6], [8, 10], [12, 14]])
@expect_assignment(3, [[0, 2, 4], [6, 8, 10]])
@expect_assignment(4, [[0, 2, 4, 6], [8, 10, 12, 14]])
@expect_assignment(8, [list(range(0, 16, 2))])
@expect_invalid([(2, 5), (5, 2), (3, 3)])
class TestCpuCoresPerRun_singleCPU_HT(TestCpuCoresPerRun):
    use_hyperthreading = False
    machine_definition = ([8, 1], 2)

    # 0(1)  2(3)    4(5)    6(7)

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


@expect_assignment(
    1,
    [
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
    ],
)
@expect_assignment(
    2,
    [
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
    ],
)
@expect_assignment(
    3,
    [
        [0, 1, 2],
        [16, 17, 18],
        [4, 5, 6],
        [20, 21, 22],
        [8, 9, 10],
        [24, 25, 26],
        [12, 13, 14],
        [28, 29, 30],
    ],
)
@expect_assignment(
    4,
    [
        [0, 1, 2, 3],
        [16, 17, 18, 19],
        [4, 5, 6, 7],
        [20, 21, 22, 23],
        [8, 9, 10, 11],
        [24, 25, 26, 27],
        [12, 13, 14, 15],
        [28, 29, 30, 31],
    ],
)
@expect_assignment(
    8,
    [
        [0, 1, 2, 3, 4, 5, 6, 7],
        [16, 17, 18, 19, 20, 21, 22, 23],
        [8, 9, 10, 11, 12, 13, 14, 15],
        [24, 25, 26, 27, 28, 29, 30, 31],
    ],
)
@expect_invalid([(2, 17), (17, 2), (4, 9), (9, 4), (8, 5), (5, 8)])
@expect_valid([(16, 2)], [lrange(0, 16), lrange(16, 32)])
class TestCpuCoresPerRun_dualCPU_HT(TestCpuCoresPerRun):
    use_hyperthreading = True
    machine_definition = ([16, 2], 2)

    # Note: the core assignment here is non-uniform, the last two threads are spread over three physical cores
    # Currently, the assignment algorithm cannot do better for odd coreLimits,
    # but this affects only cases where physical cores are split between runs, which is not recommended anyway.


@expect_assignment(1, [[x] for x in [0, 5, 10, 1, 6, 11, 2, 7, 12, 3, 8, 13, 4, 9, 14]])
@expect_assignment(
    2,
    [
        [0, 1],
        [5, 6],
        [10, 11],
        [2, 3],
        [7, 8],
        [12, 13],
    ],
    6,
)
@expect_assignment(3, [[0, 1, 2], [5, 6, 7], [10, 11, 12]], 3)
@expect_assignment(4, [[0, 1, 2, 3], [5, 6, 7, 8], [10, 11, 12, 13]])
@expect_assignment(8, [[0, 1, 2, 3, 4, 5, 6, 7]])
@expect_invalid([(6, 2)])
class TestCpuCoresPerRun_threeCPU(TestCpuCoresPerRun):
    use_hyperthreading = False
    machine_definition = ([15, 3], 1)


@expect_assignment(
    1, [[x] for x in [0, 10, 20, 2, 12, 22, 4, 14, 24, 6, 16, 26, 8, 18, 28]]
)
@expect_assignment(
    2,
    [
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
    ],
)
@expect_assignment(
    3,
    [
        [0, 1, 2],
        [10, 11, 12],
        [20, 21, 22],
        [4, 5, 6],
        [14, 15, 16],
        [24, 25, 26],
    ],
    6,
)
@expect_assignment(
    4,
    [
        [0, 1, 2, 3],
        [10, 11, 12, 13],
        [20, 21, 22, 23],
        [4, 5, 6, 7],
        [14, 15, 16, 17],
        [24, 25, 26, 27],
    ],
    6,
)
@expect_assignment(
    8,
    [
        [0, 1, 2, 3, 4, 5, 6, 7],
        [10, 11, 12, 13, 14, 15, 16, 17],
        [20, 21, 22, 23, 24, 25, 26, 27],
    ],
)
@expect_invalid([(11, 2)])
class TestCpuCoresPerRun_threeCPU_HT(TestCpuCoresPerRun):
    use_hyperthreading = True
    machine_definition = ([15, 3], 2)

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


@expect_invalid(
    [
        (2, 33),
        (33, 2),
        (3, 21),
        (17, 3),
        (4, 17),
        (17, 4),
        (5, 13),
        (9, 5),
        (6, 9),
        (9, 6),
        (7, 9),
        (9, 7),
        (8, 9),
        (9, 8),
        (9, 5),
        (6, 9),
        (10, 5),
        (6, 10),
        (11, 5),
        (6, 11),
        (12, 5),
        (6, 12),
        (13, 5),
        (5, 13),
        (14, 5),
        (5, 14),
        (15, 5),
        (5, 15),
        (16, 5),
        (5, 16),
    ]
)
@expect_valid(
    [(16, 4)],
    [
        lrange(0, 16),
        lrange(16, 32),
        lrange(32, 48),
        lrange(48, 64),
    ],
)
@expect_valid([(64, 1), (2, 32), (32, 2), (16, 3), (4, 16), (16, 4), (8, 8)], None)
class TestCpuCoresPerRun_quadCPU_HT(TestCpuCoresPerRun):
    use_hyperthreading = True
    machine_definition = ([32, 4], 2)

    # Just test that no exception occurs
    # Commented out tests are not longer possible
    # self.assertValid(1, 64) - we do not divide HT siblings
    # self.assertValid(3, 20) - we do not divide HT siblings: 4*20 = 80
    # self.assertValid(5, 12) - we do not divide HT siblings: 6*12 =72


@expect_assignment(1, [[x] for x in [0, 2, 4, 6]])
@expect_assignment(2, [[0, 2], [4, 6]])
@expect_assignment(3, [[0, 2, 4]])
@expect_assignment(4, [[0, 2, 4, 6]])
@expect_invalid([(1, 5), (2, 3), (3, 2), (4, 2), (8, 1)])
class TestCpuCoresPerRun_singleCPU_no_ht(TestCpuCoresPerRun):
    use_hyperthreading = False
    machine_definition = ([4, 1], 2)


@expect_assignment(1, [[0], [8], [2], [10], [4], [12], [6], [14]])
@expect_assignment(2, [[0, 2], [8, 10], [4, 6], [12, 14]])
@expect_assignment(3, [[0, 2, 4], [8, 10, 12]])
@expect_assignment(4, [[0, 2, 4, 6], [8, 10, 12, 14]])
@expect_assignment(8, [[0, 2, 4, 6, 8, 10, 12, 14]])
@expect_invalid(
    [(1, 9), (1, 10), (2, 5), (2, 6), (3, 3), (3, 4), (4, 3), (4, 4), (8, 2), (8, 3)]
)
class TestCpuCoresPerRun_dualCPU_no_ht(TestCpuCoresPerRun):
    use_hyperthreading = False
    machine_definition = ([8, 2], 2)


@expect_assignment(1, [[x] for x in [0, 6, 12, 2, 8, 14, 4, 10, 16]])
@expect_assignment(2, [[0, 2], [6, 8], [12, 14]], 3)
@expect_assignment(3, [[0, 2, 4], [6, 8, 10], [12, 14, 16]])
@expect_assignment(4, [[0, 2, 4, 6]], 1)
@expect_assignment(8, [[0, 2, 4, 6, 8, 10, 12, 14]])
@expect_invalid([(1, 10), (2, 4), (3, 4), (4, 2), (8, 2)])
class TestCpuCoresPerRun_threeCPU_no_ht(TestCpuCoresPerRun):
    use_hyperthreading = False
    machine_definition = ([9, 3], 2)


@expect_assignment(
    1, [[x] for x in [0, 8, 16, 24, 2, 10, 18, 26, 4, 12, 20, 28, 6, 14, 22, 30]]
)
@expect_assignment(
    2,
    [
        [0, 2],
        [8, 10],
        [16, 18],
        [24, 26],
        [4, 6],
        [12, 14],
        [20, 22],
        [28, 30],
    ],
)
@expect_assignment(3, [[0, 2, 4], [8, 10, 12], [16, 18, 20], [24, 26, 28]], 4)
@expect_assignment(
    4,
    [
        [0, 2, 4, 6],
        [8, 10, 12, 14],
        [16, 18, 20, 22],
        [24, 26, 28, 30],
    ],
)
@expect_assignment(
    8,
    [
        [0, 2, 4, 6, 8, 10, 12, 14],
        [16, 18, 20, 22, 24, 26, 28, 30],
    ],
)
@expect_invalid([(1, 17), (2, 9), (3, 5), (4, 5), (8, 3)])
@expect_invalid([(5, 3), (6, 3)])
@expect_valid([(5, 2)], [[0, 2, 4, 6, 8], [16, 18, 20, 22, 24]])
@expect_valid([(6, 2)], [[0, 2, 4, 6, 8, 10], [16, 18, 20, 22, 24, 26]])
class TestCpuCoresPerRun_quadCPU_no_ht(TestCpuCoresPerRun):
    use_hyperthreading = False
    machine_definition = ([16, 4], 2)


@expect_assignment(1, [[x] for x in [0, 8, 2, 10, 4, 12, 6, 14]])
@expect_assignment(2, [[0, 2], [8, 10], [4, 6], [12, 14]])
@expect_assignment(3, [[0, 2, 4], [8, 10, 12]])
@expect_assignment(4, [[0, 2, 4, 6], [8, 10, 12, 14]])
@expect_assignment(5, [[0, 2, 4, 6, 8]])
@expect_assignment(8, [[0, 2, 4, 6, 8, 10, 12, 14]])
@expect_invalid([(2, 5), (5, 2), (3, 3)])
class Test_Topology_P1_NUMA2_L8_C16_F(TestCpuCoresPerRun):
    use_hyperthreading = False
    machine_definition = ([8, 8, 2, 1], 2)

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


@expect_assignment(1, [[x] for x in [0, 8, 2, 10, 4, 12, 6, 14]])
@expect_assignment(
    2,
    [
        [0, 1],
        [8, 9],
        [2, 3],
        [10, 11],
        [4, 5],
        [12, 13],
        [6, 7],
        [14, 15],
    ],
)
@expect_assignment(3, [[0, 1, 2], [8, 9, 10], [4, 5, 6], [12, 13, 14]])
@expect_assignment(4, [[0, 1, 2, 3], [8, 9, 10, 11], [4, 5, 6, 7], [12, 13, 14, 15]])
@expect_assignment(8, [[0, 1, 2, 3, 4, 5, 6, 7], [8, 9, 10, 11, 12, 13, 14, 15]])
@expect_invalid([(2, 9), (4, 5), (3, 5)])
class Test_Topology_P1_NUMA2_L8_C16_T(TestCpuCoresPerRun):
    use_hyperthreading = True
    machine_definition = ([8, 8, 2, 1], 2)


@expect_assignment(1, [[x] for x in [0, 4, 8, 2, 6, 10]])
@expect_assignment(2, [[0, 2], [4, 6], [8, 10]])
@expect_assignment(3, [[0, 2, 4]], 1)
@expect_assignment(4, [[0, 2, 4, 6]])
@expect_invalid([(2, 4), (3, 2), (4, 2)])
class Test_Topology_P1_NUMA3_L6_C12_F(TestCpuCoresPerRun):
    use_hyperthreading = False
    machine_definition = ([6, 6, 3, 1], 2)
    """                             x                                           P

            x                       x                       x                   NUMA

        x       x               x       x               x       x               L3

    0   (1)     2   (3)     4   (5)     6   (7)     8   (9)     10     (11)     cores
    """


@expect_assignment(1, [[x] for x in [0, 4, 8, 2, 6, 10]])
@expect_assignment(2, [[0, 1], [4, 5], [8, 9], [2, 3], [6, 7], [10, 11]])
@expect_assignment(3, [[0, 1, 2], [4, 5, 6], [8, 9, 10]])
@expect_assignment(4, [[0, 1, 2, 3], [4, 5, 6, 7], [8, 9, 10, 11]])
@expect_assignment(5, [[0, 1, 2, 3, 4]], 1)
@expect_assignment(8, [[0, 1, 2, 3, 4, 5, 6, 7]])
@expect_invalid([(2, 7), (3, 4), (4, 4), (5, 2)])
class Test_Topology_P1_NUMA3_L6_C12_T(TestCpuCoresPerRun):
    use_hyperthreading = True
    machine_definition = ([6, 6, 3, 1], 2)
    """                             x                                           P

            x                       x                       x                   NUMA

        x       x               x       x               x       x               L3

    0   1     2    3        4     5     6   7       8   9     10    11          cores
    """


@expect_assignment(1, [[x] for x in [0, 8, 4, 12, 2, 10, 6, 14]])
@expect_assignment(2, [[0, 2], [8, 10], [4, 6], [12, 14]])
@expect_assignment(3, [[0, 2, 4], [8, 10, 12]])
@expect_assignment(4, [[0, 2, 4, 6], [8, 10, 12, 14]])
@expect_assignment(8, [[0, 2, 4, 6, 8, 10, 12, 14]])
@expect_invalid([(2, 5), (3, 3), (4, 3), (8, 2)])
class Test_Topology_P2_NUMA4_L8_C16_F(TestCpuCoresPerRun):
    use_hyperthreading = False
    machine_definition = ([8, 8, 4, 2], 2)


@expect_assignment(1, [[x] for x in [0, 8, 4, 12, 2, 10, 6, 14]])
@expect_assignment(
    2,
    [
        [0, 1],
        [8, 9],
        [4, 5],
        [12, 13],
        [2, 3],
        [10, 11],
        [6, 7],
        [14, 15],
    ],
)
@expect_assignment(3, [[0, 1, 2], [8, 9, 10], [4, 5, 6], [12, 13, 14]])
@expect_assignment(4, [[0, 1, 2, 3], [8, 9, 10, 11], [4, 5, 6, 7], [12, 13, 14, 15]])
@expect_assignment(8, [[0, 1, 2, 3, 4, 5, 6, 7], [8, 9, 10, 11, 12, 13, 14, 15]])
@expect_invalid([(2, 9), (3, 5), (4, 5), (8, 3)])
class Test_Topology_P2_NUMA4_L8_C16_T(TestCpuCoresPerRun):
    use_hyperthreading = True
    machine_definition = ([8, 8, 4, 2], 2)


@expect_assignment(1, [[x] for x in [0, 8, 4, 12, 2, 10, 6, 14]])
@expect_assignment(2, [[0, 2], [8, 10], [4, 6], [12, 14]])
@expect_assignment(3, [[0, 2, 4], [8, 10, 12]])
@expect_assignment(4, [[0, 2, 4, 6], [8, 10, 12, 14]])
@expect_assignment(8, [[0, 2, 4, 6, 8, 10, 12, 14]])
@expect_invalid([(2, 5), (3, 3), (4, 3), (8, 2)])
class Test_Topology_P1_G2_NUMA4_L8_C16_F(TestCpuCoresPerRun):
    use_hyperthreading = False
    machine_definition = ([8, 8, 4, 2, 1], 2)


@expect_assignment(1, [[x] for x in [0, 8, 4, 12, 2, 10, 6, 14]])
@expect_assignment(
    2,
    [
        [0, 1],
        [8, 9],
        [4, 5],
        [12, 13],
        [2, 3],
        [10, 11],
        [6, 7],
        [14, 15],
    ],
)
@expect_assignment(3, [[0, 1, 2], [8, 9, 10], [4, 5, 6], [12, 13, 14]])
@expect_assignment(4, [[0, 1, 2, 3], [8, 9, 10, 11], [4, 5, 6, 7], [12, 13, 14, 15]])
@expect_assignment(8, [[0, 1, 2, 3, 4, 5, 6, 7], [8, 9, 10, 11, 12, 13, 14, 15]])
@expect_invalid([(2, 9), (3, 5), (4, 5), (8, 3)])
class Test_Topology_P1_G2_NUMA4_L8_C16_T(TestCpuCoresPerRun):
    use_hyperthreading = True
    machine_definition = ([8, 8, 4, 2, 1], 2)


@expect_assignment(1, [[x] for x in [0, 6, 3, 9]])
@expect_assignment(2, [[0, 3], [6, 9]])
@expect_assignment(3, [[0, 3, 6]])
@expect_assignment(4, [[0, 3, 6, 9]])
@expect_invalid([(2, 3), (3, 2), (4, 2), (8, 3)])
class Test_Topology_P1_NUMA2_L4_C12_F3(TestCpuCoresPerRun):
    use_hyperthreading = False
    machine_definition = ([4, 4, 2, 1], 3)


@expect_assignment(1, [[x] for x in [0, 6, 3, 9]])
@expect_assignment(2, [[0, 1], [6, 7], [3, 4], [9, 10]])
@expect_assignment(3, [[0, 1, 2], [6, 7, 8], [3, 4, 5], [9, 10, 11]])
@expect_assignment(4, [[0, 1, 2, 3], [6, 7, 8, 9]])
@expect_assignment(8, [[0, 1, 2, 3, 4, 5, 6, 7]])
@expect_invalid([(2, 5), (3, 5), (4, 3), (8, 2)])
class Test_Topology_P1_NUMA2_L4_C12_T3(TestCpuCoresPerRun):
    use_hyperthreading = True
    machine_definition = ([4, 4, 2, 1], 3)


# fmt: off
@expect_assignment(
    1,
    [[x] for x in [
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
)
@expect_assignment(
    2,
    [
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
)
@expect_assignment(
    3,
    [
        [0, 1, 2], [128, 129, 130], [32, 33, 34], [160, 161, 162], [64, 65, 66], [192, 193, 194], [96, 97, 98], [224, 225, 226],
        [16, 17, 18], [144, 145, 146], [48, 49, 50], [176, 177, 178], [80, 81, 82], [208, 209, 210], [112, 113, 114], [240, 241, 242],
        [4, 5, 6], [132, 133, 134], [36, 37, 38], [164, 165, 166], [68, 69, 70], [196, 197, 198], [100, 101, 102], [228, 229, 230],
        [20, 21, 22], [148, 149, 150], [52, 53, 54], [180, 181, 182], [84, 85, 86], [212, 213, 214], [116, 117, 118], [244, 245, 246],
        [8, 9, 10], [136, 137, 138], [40, 41, 42], [168, 169, 170], [72, 73, 74], [200, 201, 202], [104, 105, 106], [232, 233, 234],
        [24, 25, 26], [152, 153, 154], [56, 57, 58], [184, 185, 186], [88, 89, 90], [216, 217, 218], [120, 121, 122], [248, 249, 250],
        [12, 13, 14], [140, 141, 142], [44, 45, 46], [172, 173, 174], [76, 77, 78], [204, 205, 206], [108, 109, 110], [236, 237, 238],
        [28, 29, 30], [156, 157, 158], [60, 61, 62], [188, 189, 190], [92, 93, 94], [220, 221, 222], [124, 125, 126], [252, 253, 254],
    ]
)
@expect_assignment(
    4,
    [
        [0, 1, 2, 3], [128, 129, 130, 131], [32, 33, 34, 35], [160, 161, 162, 163], [64, 65, 66, 67], [192, 193, 194, 195], [96, 97, 98, 99], [224, 225, 226, 227],
        [16, 17, 18, 19], [144, 145, 146, 147], [48, 49, 50, 51], [176, 177, 178, 179], [80, 81, 82, 83], [208, 209, 210, 211], [112, 113, 114, 115], [240, 241, 242, 243],
        [4, 5, 6, 7], [132, 133, 134, 135], [36, 37, 38, 39], [164, 165, 166, 167], [68, 69, 70, 71], [196, 197, 198, 199], [100, 101, 102, 103], [228, 229, 230, 231],
        [20, 21, 22, 23], [148, 149, 150, 151], [52, 53, 54, 55], [180, 181, 182, 183], [84, 85, 86, 87], [212, 213, 214, 215], [116, 117, 118, 119], [244, 245, 246, 247],
        [8, 9, 10, 11], [136, 137, 138, 139], [40, 41, 42, 43], [168, 169, 170, 171], [72, 73, 74, 75], [200, 201, 202, 203], [104, 105, 106, 107], [232, 233, 234, 235],
        [24, 25, 26, 27], [152, 153, 154, 155], [56, 57, 58, 59], [184, 185, 186, 187], [88, 89, 90, 91], [216, 217, 218, 219], [120, 121, 122, 123], [248, 249, 250, 251],
        [12, 13, 14, 15], [140, 141, 142, 143], [44, 45, 46, 47], [172, 173, 174, 175], [76, 77, 78, 79], [204, 205, 206, 207], [108, 109, 110, 111], [236, 237, 238, 239],
        [28, 29, 30, 31], [156, 157, 158, 159], [60, 61, 62, 63], [188, 189, 190, 191], [92, 93, 94, 95], [220, 221, 222, 223], [124, 125, 126, 127], [252, 253, 254, 255],
    ]
)
@expect_assignment(
    8,
    [
        [0, 1, 2, 3, 4, 5, 6, 7], [128, 129, 130, 131, 132, 133, 134, 135], [32, 33, 34, 35, 36, 37, 38, 39], [160, 161, 162, 163, 164, 165, 166, 167], [64, 65, 66, 67, 68, 69, 70, 71], [192, 193, 194, 195, 196, 197, 198, 199], [96, 97, 98, 99, 100, 101, 102, 103], [224, 225, 226, 227, 228, 229, 230, 231],
        [16, 17, 18, 19, 20, 21, 22, 23], [144, 145, 146, 147, 148, 149, 150, 151], [48, 49, 50, 51, 52, 53, 54, 55], [176, 177, 178, 179, 180, 181, 182, 183], [80, 81, 82, 83, 84, 85, 86, 87], [208, 209, 210, 211, 212, 213, 214, 215], [112, 113, 114, 115, 116, 117, 118, 119], [240, 241, 242, 243, 244, 245, 246, 247],
        [8, 9, 10, 11, 12, 13, 14, 15], [136, 137, 138, 139, 140, 141, 142, 143], [40, 41, 42, 43, 44, 45, 46, 47], [168, 169, 170, 171, 172, 173, 174, 175], [72, 73, 74, 75, 76, 77, 78, 79], [200, 201, 202, 203, 204, 205, 206, 207], [104, 105, 106, 107, 108, 109, 110, 111], [232, 233, 234, 235, 236, 237, 238, 239],
        [24, 25, 26, 27, 28, 29, 30, 31], [152, 153, 154, 155, 156, 157, 158, 159], [56, 57, 58, 59, 60, 61, 62, 63], [184, 185, 186, 187, 188, 189, 190, 191], [88, 89, 90, 91, 92, 93, 94, 95], [216, 217, 218, 219, 220, 221, 222, 223], [120, 121, 122, 123, 124, 125, 126, 127], [248, 249, 250, 251, 252, 253, 254, 255],
    ]
)
# fmt: on
class Test_Topology_P2_G2_NUMA8_L16_C256_T(TestCpuCoresPerRun):
    use_hyperthreading = True
    machine_definition = ([128, 16, 8, 2, 2], 2)


# prevent execution of base class as its own test
del TestCpuCoresPerRun
