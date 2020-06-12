// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import {
  isOkStatus,
  numericSortMethod,
  textSortMethod,
  getHashSearch,
  setHashSearch,
} from "../utils/utils";

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

describe("numericSortMethod", () => {
  test("should evaluate order of objects with different values", () => {
    const bigger = { raw: 9001 };
    const smaller = { raw: 1337 };
    expect(numericSortMethod(bigger, smaller)).toBeGreaterThan(0);
    expect(numericSortMethod(smaller, bigger)).toBeLessThan(0);
  });

  test("should evaluate order of objects with same values", () => {
    const even1 = { raw: 1 };
    const even2 = { raw: 1 };
    expect(numericSortMethod(even1, even2)).toBe(0);
  });

  test("should order items without raw prop last", () => {
    const testObject = { raw: 1 };
    const objectWithoutProp = { fake: 1 };
    expect(numericSortMethod(objectWithoutProp, testObject)).toBeGreaterThan(0);
    expect(numericSortMethod(testObject, objectWithoutProp)).toBeLessThan(0);
  });

  test("should be nil safe", () => {
    const testObject = { raw: 1 };
    expect(numericSortMethod(null, testObject)).toBeGreaterThan(0);
    expect(numericSortMethod(undefined, testObject)).toBeGreaterThan(0);
    expect(numericSortMethod(testObject, null)).toBeLessThan(0);
    expect(numericSortMethod(testObject, undefined)).toBeLessThan(0);
  });
});

describe("hashRouting helpers", () => {
  describe("getHashSearch", () => {
    test("should get params as object", () => {
      const res = getHashSearch("localhost#/bla?id=1&name=benchexec");
      expect(res).toMatchObject({ id: "1", name: "benchexec" });
    });

    test("should return empty object if no params are given", () => {
      const res = getHashSearch("localhost#bla");
      expect(res).toMatchObject({});
    });

    test("should return empty object if only ? is given", () => {
      const res = getHashSearch("localhost#bla?");
      expect(res).toMatchObject({});
    });
  });

  describe("setHashSearch", () => {
    test("should translate object to queryparams", () => {
      const params = { id: "1", name: "benchexec" };
      const res = setHashSearch(params, {
        returnString: true,
        baseUrl: "localhost#table",
      });
      expect(res).toEqual("localhost#table?id=1&name=benchexec");
    });
  });
});

describe("textSortMethod", () => {
  test("should evaluate order of objects with different values", () => {
    const smaller = { raw: "a" };
    const bigger = { raw: "b" };
    expect(textSortMethod(bigger, smaller)).toBeGreaterThan(0);
    expect(textSortMethod(smaller, bigger)).toBeLessThan(0);
  });

  test("should sort strings with different values without case sensitivy", () => {
    const smaller = { raw: "a" };
    const bigger = { raw: "B" };
    expect(textSortMethod(bigger, smaller)).toBeGreaterThan(0);
    expect(textSortMethod(smaller, bigger)).toBeLessThan(0);
  });

  test("should evaluate order of objects with same values", () => {
    const even1 = { raw: "a" };
    const even2 = { raw: "a" };
    expect(textSortMethod(even1, even2)).toBe(0);
  });

  test("should sort strings with same values without case sensitivity", () => {
    const even1 = { raw: "a" };
    const even2 = { raw: "A" };
    expect(textSortMethod(even1, even2)).toBe(0);
  });

  test("should sort empty value last", () => {
    const bigger = { raw: "" };
    const smaller = { raw: "a" };
    expect(textSortMethod(bigger, smaller)).toBeGreaterThan(0);
    expect(textSortMethod(smaller, bigger)).toBeLessThan(0);
  });

  test("should order items without raw prop last", () => {
    const testObject = { raw: "a" };
    const objectWithoutProp = { fake: "a" };
    expect(textSortMethod(objectWithoutProp, testObject)).toBeGreaterThan(0);
    expect(textSortMethod(testObject, objectWithoutProp)).toBeLessThan(0);
  });

  test("should be nil safe", () => {
    const testObject = { raw: "a" };
    expect(textSortMethod(null, testObject)).toBeGreaterThan(0);
    expect(textSortMethod(undefined, testObject)).toBeGreaterThan(0);
    expect(textSortMethod(testObject, null)).toBeLessThan(0);
    expect(textSortMethod(testObject, undefined)).toBeLessThan(0);
  });
});
