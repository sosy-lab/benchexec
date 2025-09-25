# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2024 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import unittest
from benchexec.resources import frequency_filter, get_closest_nodes

# High-level tests for the allocation algorithm are in test_core_assignment.py


class TestFrequencyFilter(unittest.TestCase):
    def test_single_cpu(self):
        self.assertEqual(frequency_filter({1000: [0]}), [0])

    def test_all_equal(self):
        self.assertEqual(frequency_filter({1000: [0, 1, 2, 3, 4]}), [0, 1, 2, 3, 4])

    def test_all_fast(self):
        self.assertEqual(
            frequency_filter({1000: [0, 1], 950: [2, 3], 999: [4, 5]}),
            [0, 1, 2, 3, 4, 5],
        )

    def test_mixed(self):
        self.assertEqual(
            frequency_filter(
                {1000: [0, 1], 950: [2, 3], 999: [4, 5], 949: [6, 7], 500: [8, 9]}
            ),
            [0, 1, 2, 3, 4, 5],
        )

    def test_assymetric_counts(self):
        self.assertEqual(
            frequency_filter(
                {
                    1000: [0],
                    950: [1, 2],
                    999: [3, 4, 5],
                    949: [6, 7, 8, 9],
                    500: [10, 11],
                }
            ),
            [0, 1, 2, 3, 4, 5],
        )


class TestGetClosestNodes(unittest.TestCase):
    def test_single_node(self):
        self.assertEqual(get_closest_nodes([10]), [0])

    def test_dual_node(self):
        self.assertEqual(get_closest_nodes([10, 21]), [0])
        self.assertEqual(get_closest_nodes([21, 0]), [1])

    def test_quad_node(self):
        self.assertEqual(get_closest_nodes([10, 11, 11, 11]), [0])
        self.assertEqual(get_closest_nodes([20, 10, 20, 20]), [1])
        self.assertEqual(get_closest_nodes([32, 32, 10, 32]), [2])
        self.assertEqual(get_closest_nodes([32, 32, 32, 10]), [3])

    def test_hierarchical_nodes(self):
        self.assertEqual(
            get_closest_nodes([10, 11, 11, 11, 20, 20, 20, 20]), [0, 1, 2, 3]
        )
        self.assertEqual(
            get_closest_nodes([20, 20, 20, 20, 11, 10, 11, 11]), [5, 4, 6, 7]
        )

    def test_dual_epyc_7713(self):
        self.assertEqual(
            get_closest_nodes(
                [10, 11, 12, 12, 12, 12, 12, 12, 32, 32, 32, 32, 32, 32, 32, 32]
            ),
            [0, 1],
        )
        self.assertEqual(
            get_closest_nodes(
                [11, 10, 12, 12, 12, 12, 12, 12, 32, 32, 32, 32, 32, 32, 32, 32]
            ),
            [1, 0],
        )
        self.assertEqual(
            get_closest_nodes(
                [12, 12, 10, 11, 12, 12, 12, 12, 32, 32, 32, 32, 32, 32, 32, 32]
            ),
            [2, 3],
        )
        self.assertEqual(
            get_closest_nodes(
                [12, 12, 11, 10, 12, 12, 12, 12, 32, 32, 32, 32, 32, 32, 32, 32]
            ),
            [3, 2],
        )
        self.assertEqual(
            get_closest_nodes(
                [12, 12, 12, 12, 12, 12, 10, 11, 32, 32, 32, 32, 32, 32, 32, 32]
            ),
            [6, 7],
        )
        self.assertEqual(
            get_closest_nodes(
                [12, 12, 12, 12, 12, 12, 11, 10, 32, 32, 32, 32, 32, 32, 32, 32]
            ),
            [7, 6],
        )
        self.assertEqual(
            get_closest_nodes(
                [32, 32, 32, 32, 32, 32, 32, 32, 10, 11, 12, 12, 12, 12, 12, 12]
            ),
            [8, 9],
        )
        self.assertEqual(
            get_closest_nodes(
                [32, 32, 32, 32, 32, 32, 32, 32, 11, 10, 12, 12, 12, 12, 12, 12]
            ),
            [9, 8],
        )
        self.assertEqual(
            get_closest_nodes(
                [32, 32, 32, 32, 32, 32, 32, 32, 12, 12, 12, 12, 12, 12, 10, 11]
            ),
            [14, 15],
        )
        self.assertEqual(
            get_closest_nodes(
                [32, 32, 32, 32, 32, 32, 32, 32, 12, 12, 12, 12, 12, 12, 11, 10]
            ),
            [15, 14],
        )

    def test_more_than_one_smallest(self):
        self.assertRaises(Exception, lambda: get_closest_nodes([10, 10]))
        self.assertRaises(Exception, lambda: get_closest_nodes([10, 20, 10, 20]))
