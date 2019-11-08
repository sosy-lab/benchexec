/* SPDX-License-Identifier: Apache-2.0
 *
 * BenchExec is a framework for reliable benchmarking.
 * This file is part of BenchExec.
 * Copyright (C) Dirk Beyer. All rights reserved.
 */
import {
  applyFilter,
  isOkStatus,
  maybeTransformToLowercase,
  sortMethod
} from "../utils/utils";

//Example data set to test the filtering by regex
const rows = [
  {
    test: {
      raw: "10.5"
    }
  },
  {
    test: {
      raw: "10"
    }
  },
  {
    test: {
      html: "9.3",
      raw: "9.30"
    }
  },
  {
    test: {
      html: "11",
      raw: "11.0"
    }
  },
  {
    test: {
      raw: "11.001"
    }
  }
];

//Function to test filtering by regex for data set 'rows' (return number of truely returnd values)
const getFilteredData = regex =>
  rows.filter(row => applyFilter({ id: "test", value: regex }, row));

test("applyFilter single entry without result", () => {
  expect(
    applyFilter(
      {
        id: "test",
        value: "10:"
      },
      {
        test: {
          raw: "7"
        }
      }
    )
  ).toBe(false);
});

//use function getFilteredData to generate test cases with data set 'rows'

test("applyFilter greater 10", () => {
  expect(getFilteredData("10:").length).toBe(4);
});

test("applyFilter equals 10", () => {
  expect(getFilteredData("10").length).toBe(2);
});

test("applyFilter between 10.3 and 10.7", () => {
  expect(getFilteredData("10.3:10.7").length).toBe(1);
});

describe("isStatusOk", () => {
  test("should return true if status code is 0", () => {
    expect(isOkStatus(0)).toBe(true);
  });
  test("should return true if status code is 200", () => {
    expect(isOkStatus(200)).toBe(true);
  });
  test("should return false if other integer is passed", () => {
    expect(isOkStatus(404)).toBe(false);
  });
  test("should return false if string is passed", () => {
    expect(isOkStatus("hi there")).toBe(false);
  });
  test("should return false if object is passed", () => {
    expect(isOkStatus({ a: "b" })).toBe(false);
  });
  test("should return false if nothing is passed", () => {
    expect(isOkStatus()).toBe(false);
  });
});

describe("maybeTransformToLowercase", () => {
  test("should transform to lowercase if string is passed", () => {
    expect(maybeTransformToLowercase("BIG")).toBe("big");
  });

  test("should not try to transform to lowercase if number is passed", () => {
    expect(maybeTransformToLowercase(1)).toBe(1);
  });

  test("should not try to transform to lowercase if object is passed", () => {
    const obj = { a: "b" };
    expect(maybeTransformToLowercase(obj)).toBe(obj);
  });

  test("should not try to transform to lowercase if array is passed", () => {
    expect(maybeTransformToLowercase([1])).toEqual([1]);
  });

  test("should not try to transform to lowercase if nil is passed", () => {
    expect(maybeTransformToLowercase(undefined)).toBe(undefined);
  });
});

describe("sortMethod", () => {
  test("should evaluate order of objects with different values", () => {
    const bigger = { raw: 9001 };
    const smaller = { raw: 1337 };
    expect(sortMethod(bigger, smaller)).toBeLessThan(0);
    expect(sortMethod(smaller, bigger)).toBeGreaterThan(0);
  });

  test("should evaluate order of objects with same values", () => {
    const even1 = { raw: 1 };
    const even2 = { raw: 1 };
    expect(sortMethod(even1, even2)).toBe(0);
  });

  test("should order items without raw prop last", () => {
    const testObject = { raw: 1 };
    const objectWithoutProp = { fake: 1 };
    expect(sortMethod(testObject, objectWithoutProp)).toBe(-Infinity);
  });

  test("should be nil safe", () => {
    const testObject = { raw: 1 };
    expect(sortMethod(testObject, null)).toBe(-Infinity);
    expect(sortMethod(testObject, undefined)).toBe(-Infinity);
  });
});
