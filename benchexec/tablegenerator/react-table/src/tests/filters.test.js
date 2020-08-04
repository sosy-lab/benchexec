// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import { applyNumericFilter } from "../utils/filters";

//Example data set to test the filtering by regex
const rows = [
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
];

//Function to test filtering by regex for data set 'rows' (return number of truely returnd values)
const getFilteredData = (regex) =>
  rows.filter((row) => applyNumericFilter({ id: "test", value: regex }, row));

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
  expect(getFilteredData("10:").length).toBe(4);
});

test("applyNumericFilter less than 10", () => {
  expect(getFilteredData(":10").length).toBe(3);
});

test("applyNumericFilter equals 10", () => {
  expect(getFilteredData("10").length).toBe(2);
});

test("applyNumericFilter between 10.3 and 10.7", () => {
  expect(getFilteredData("10.3:10.7").length).toBe(1);
});

test("applyNumericFilter non-positive numbers", () => {
  expect(getFilteredData(":0").length).toBe(1);
});

test("applyNumericFilter non-negative numbers", () => {
  expect(getFilteredData("0:").length).toBe(5);
});

test("applyNumericFilter all numbers", () => {
  expect(getFilteredData(":").length).toBe(6);
});

test("applyNumericFilter with string", () => {
  expect(getFilteredData("a").length).toBe(0);
});
