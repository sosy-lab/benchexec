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
  NumberFormatterBuilder,
  hasSameEntries,
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

describe("NumberFormatterBuilder", () => {
  let builder;
  beforeEach(() => {
    builder = new NumberFormatterBuilder(4);
  });
  test("should not count decimal point as significant number", () => {
    const formatter = builder.build();

    const number = "12.34";

    expect(formatter(number)).toBe("12.34");
  });

  test("should correctly format numbers with integral and fractional parts", () => {
    const formatter = builder.build();

    const number = "12.30000000123";

    expect(formatter(number)).toBe("12.30");
  });

  test("should handle if postfix has a decimal point", () => {
    const formatter = builder.build();

    const number = "1234.342";

    expect(formatter(number)).toBe("1234");
  });

  test("should handle if postfix has a leading decimal point", () => {
    const formatter = builder.build();

    const number = "12345.342";

    expect(formatter(number)).toBe("12350");
  });

  test("in fractions below 1, should add all zeros before the first non-zero digit", () => {
    const formatter = builder.build();

    const number = "0.000001234";

    expect(formatter(number)).toBe("0.000001234");
  });

  test("should identify comma and dots as decimal points", () => {
    const formatter = builder.build();

    const numberDot = "12.34";
    const numberComma = "12,34";

    expect(formatter(numberDot)).toBe("12.34");
    expect(formatter(numberComma)).toBe("12.34");
  });

  test("should round whole integer numbers after significant digits have been reached", () => {
    const formatter = builder.build();
    const number = "123456789";

    expect(formatter(number)).toBe("123500000");
  });

  test("should round fractions after significant digits have been reached", () => {
    const formatter = builder.build();
    const number = "0.123456789";

    expect(formatter(number)).toBe("0.1235");
  });

  test("should return number without rounding if no significant digits were provided", () => {
    const newBuilder = new NumberFormatterBuilder();
    const formatter = newBuilder.build();
    const number = "123456789";

    expect(formatter(number)).toBe("123456789");
  });

  test("should format whitespaces according to dataset context", () => {
    builder.addDataItem("1234");
    builder.addDataItem("0.12345");

    const formatter = builder.build();

    // we have 4 digits before and 5 digits after the decimal point
    const number1 = "23";
    const number2 = "23.1";
    const number3 = "0.123";
    const number4 = "0.01337";

    const expected1 = "  23      ";
    const expected2 = "  23.1    ";
    const expected3 = "    .123  ";
    const expected4 = "    .01337";

    const actual1 = formatter(number1, { whitespaceFormat: true });
    const actual2 = formatter(number2, { whitespaceFormat: true });
    const actual3 = formatter(number3, { whitespaceFormat: true });
    const actual4 = formatter(number4, { whitespaceFormat: true });

    expect(actual1).toBe(expected1);
    expect(actual2).toBe(expected2);
    expect(actual3).toBe(expected3);
    expect(actual4).toBe(expected4);
  });

  test("should format whitespaces with html", () => {
    builder.addDataItem("1234");
    builder.addDataItem("0.12345");

    const formatter = builder.build();

    // we have 4 digits before and 5 digits after the decimal point
    const number1 = "23";
    const number2 = "23.1";
    const number3 = "0.123";
    const number4 = "0.01337";

    const expected1 = "  23&#x2008;     ".replace(/ /g, "&#x2007;");
    const expected2 = "  23.1    ".replace(/ /g, "&#x2007;");
    const expected3 = "    .123  ".replace(/ /g, "&#x2007;");
    const expected4 = "    .01337".replace(/ /g, "&#x2007;");

    const actual1 = formatter(number1, { whitespaceFormat: true, html: true });
    const actual2 = formatter(number2, { whitespaceFormat: true, html: true });
    const actual3 = formatter(number3, { whitespaceFormat: true, html: true });
    const actual4 = formatter(number4, { whitespaceFormat: true, html: true });

    expect(actual1).toBe(expected1);
    expect(actual2).toBe(expected2);
    expect(actual3).toBe(expected3);
    expect(actual4).toBe(expected4);
  });
});

describe(
  "textSortMethod",
  () => {
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
  },

  describe("hasSameEntries", () => {
    test("should return true if the same arrays are passed", () => {
      const a = ["a", "b", "c"];
      const b = ["a", "b", "c"];
      expect(hasSameEntries(a, b)).toBe(true);
    });

    test("should return true if the same elements are present but in different order", () => {
      const a = ["a", "b", "c"];
      const b = ["c", "a", "b"];
      expect(hasSameEntries(a, b)).toBe(true);
    });

    test("should return true if the second array is a subset of the first one", () => {
      const a = ["a", "b", "c"];
      const b = ["a", "b"];
      expect(hasSameEntries(a, b)).toBe(true);
    });

    test("should return false if the second array has elements that are not in the first array", () => {
      const a = ["a", "b", "c"];
      const b = ["a", "b", "x"];
      expect(hasSameEntries(a, b)).toBe(false);
    });

    test("should return false if the first array is a subset of the second one", () => {
      const a = ["a", "b"];
      const b = ["a", "b", "c"];
      expect(hasSameEntries(a, b)).toBe(false);
    });

    test("should return false if the first array is empty", () => {
      const a = [];
      const b = ["a", "b", "c"];
      expect(hasSameEntries(a, b)).toBe(false);
    });

    test("should return true if the second array is empty", () => {
      const a = ["a", "b"];
      const b = [];
      expect(hasSameEntries(a, b)).toBe(true);
    });
  }),
);
