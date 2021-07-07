// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import {
  buildMatcher,
  applyMatcher,
  applyNumericFilter,
  statusForEmptyRows,
} from "../utils/filters";
//Example data set to test the filtering by regex
const numericRows = [
  {},
  {
    test: {},
  },
  {
    test: {
      raw: "10.5",
    },
  },
  {
    test: {
      raw: "10",
    },
  },
  {
    test: {
      html: "9.3",
      raw: "9.30",
    },
  },
  {
    test: {
      html: "11",
      raw: "11.0",
    },
  },
  {
    test: {
      raw: "11.001",
    },
  },
  {
    test: {
      raw: "-1",
    },
  },
  {
    test: {
      raw: "UNKNOWN: test",
    },
  },
];

// Example data for tests on status and category filtering
const generalRows = [
  {
    results: [
      {
        category: "correct",
        values: [
          {
            raw: "true",
          },
        ],
      },
    ],
  },
  {
    results: [
      {
        category: "correct",
        values: [
          {
            raw: "false(reach)",
          },
        ],
      },
    ],
  },
  {
    results: [
      {
        category: "missing",
        values: [
          {
            raw: "UNKNOWN: test",
          },
        ],
      },
    ],
  },
  {
    results: [
      {
        category: "empty",
        values: [{}],
      },
    ],
  },
];

//Function to test filtering by regex for data set 'rows' (return number of truely returnd values)
const getFilteredNumericalData = (regex) =>
  numericRows.filter((row) =>
    applyNumericFilter({ id: "test", value: regex }, row),
  );

const getFilteredDataWithMatcher = (filters) =>
  applyMatcher(buildMatcher(filters))(generalRows);

test("applyNumericFilter single entry without result", () => {
  expect(
    applyNumericFilter(
      {
        id: "test",
        value: "10:",
      },
      {
        test: {
          raw: "7",
        },
      },
    ),
  ).toBe(false);
});

//use function getFilteredData to generate test cases with data set 'rows'

test("applyNumericFilter greater 10", () => {
  expect(getFilteredNumericalData("10:").length).toBe(4);
});

test("applyNumericFilter less than 10", () => {
  expect(getFilteredNumericalData(":10").length).toBe(3);
});

test("applyNumericFilter equals 10", () => {
  expect(getFilteredNumericalData("10").length).toBe(2);
});

test("applyNumericFilter between 10.3 and 10.7", () => {
  expect(getFilteredNumericalData("10.3:10.7").length).toBe(1);
});

test("applyNumericFilter non-positive numbers", () => {
  expect(getFilteredNumericalData(":0").length).toBe(1);
});

test("applyNumericFilter non-negative numbers", () => {
  expect(getFilteredNumericalData("0:").length).toBe(5);
});

test("applyNumericFilter all numbers", () => {
  expect(getFilteredNumericalData(":").length).toBe(6);
});

test("applyNumericFilter with string", () => {
  expect(getFilteredNumericalData("a").length).toBe(0);
});

test("applyMatcher for all results", () => {
  const filters = [];
  expect(getFilteredDataWithMatcher(filters).length).toBe(generalRows.length);
});

test("applyMatcher for category", () => {
  const filters = [
    { id: "0_test_0", value: "correct ", type: "status" },
    { id: "0_test_0", value: "true", type: "status" },
    { id: "0_test_0", value: "false(reach)", type: "status" },
  ];
  expect(getFilteredDataWithMatcher(filters).length).toBe(2);
});

test("applyMatcher for status", () => {
  const filters = [
    { id: "0_test_0", value: "true", type: "status" },
    { id: "0_test_0", value: "correct ", type: "status" },
  ];
  expect(getFilteredDataWithMatcher(filters).length).toBe(1);
});

test("applyMatcher for status with colon", () => {
  const filters = [
    { id: "0_test_0", value: "UNKNOWN: test", type: "status" },
    { id: "0_test_0", value: "missing ", type: "status" },
  ];
  expect(getFilteredDataWithMatcher(filters).length).toBe(1);
});

test("applyMatcher for empty row", () => {
  const filters = [
    { id: "0_test_0", value: "empty ", type: "status" },
    { id: "0_test_0", value: statusForEmptyRows, type: "status" },
  ];
  expect(getFilteredDataWithMatcher(filters).length).toBe(1);
});
