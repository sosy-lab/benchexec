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
  getURLParameters,
  NumberFormatterBuilder,
  constructQueryString,
  decodeFilter,
  hasSameEntries,
  constructHashURL,
  makeFilterSerializer,
  makeFilterDeserializer,
  splitUrlPathForMatchingPrefix,
  makeRegExp,
  tokenizePart,
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
  describe("getURLParameters", () => {
    test("should get params as object", () => {
      const res = getURLParameters("localhost#/bla?id=1&name=benchexec");
      expect(res).toEqual({ id: "1", name: "benchexec" });
    });

    test("should return empty object if no params are given", () => {
      const res = getURLParameters("localhost#bla");
      expect(res).toEqual({});
    });

    test("should return empty object if only ? is given", () => {
      const res = getURLParameters("localhost#bla?");
      expect(res).toEqual({});
    });

    test("should handle missing value", () => {
      const res = getURLParameters("localhost#bla?id=1&foo");
      expect(res).toEqual({ id: "1", foo: "" });
    });

    test("should handle empty value", () => {
      const res = getURLParameters("localhost#bla?foo=&id=1");
      expect(res).toEqual({ foo: "", id: "1" });
    });

    test("should handle values with =", () => {
      const res = getURLParameters("localhost#bla?a=b=c");
      expect(res).toEqual({ a: "b=c" });
    });

    test("should handle values with ?", () => {
      const res = getURLParameters("localhost#bla?a=b?c");
      expect(res).toEqual({ a: "b?c" });
    });
  });

  describe("constructQueryString", () => {
    test("should return empty string for empty input", () => {
      const queryString = constructQueryString({});
      expect(queryString).toBe("");
    });

    test("should construct query string properly", () => {
      const params = { key1: "value1", key2: "value2" };
      const queryString = constructQueryString(params);
      expect(queryString).toBe("key1=value1&key2=value2");
    });

    test("should omit undefined and null values", () => {
      const params = { key1: "value1", key2: undefined, key3: null };
      const queryString = constructQueryString(params);
      expect(queryString).toBe("key1=value1");
    });
  });

  describe("constructHashURL", () => {
    test("should construct URL hash with provided parameters", () => {
      const baseUrl = "http://example.com";
      const params = { key1: "value1", key2: "value2" };

      const expected = {
        newUrl: "http://example.com?key1=value1&key2=value2",
        queryString: "?key1=value1&key2=value2",
      };
      expect(constructHashURL(baseUrl, params)).toEqual(expected);
    });

    test("should construct URL hash with provided parameters and keep the exisiting parameters", () => {
      const baseUrl = "http://example.com?existingKey=existingValue";
      const params = { key1: "value1", key2: "value2" };

      const expected = {
        newUrl:
          "http://example.com?existingKey=existingValue&key1=value1&key2=value2",
        queryString: "?existingKey=existingValue&key1=value1&key2=value2",
      };
      expect(constructHashURL(baseUrl, params)).toEqual(expected);
    });

    test("should return the same URL with exisiting params if no parameters are provided", () => {
      const baseUrl = "http://example.com?exisitingKey=existingValue";
      const params = {};

      const expected = {
        newUrl: "http://example.com?exisitingKey=existingValue",
        queryString: "?exisitingKey=existingValue",
      };

      expect(constructHashURL(baseUrl, params)).toEqual(expected);
    });

    test("should override existing parameters with new ones", () => {
      const baseUrl = "http://example.com?key1=value1&key2=value2";
      const params = { key2: "newValue" };

      const expected = {
        newUrl: "http://example.com?key1=value1&key2=newValue",
        queryString: "?key1=value1&key2=newValue",
      };

      expect(constructHashURL(baseUrl, params)).toEqual(expected);
    });

    test("should remove exisiting parameters if they are updated to undefined", () => {
      const baseUrl = "http://example.com?key1=value1&key2=value2";
      const params = { key2: undefined };

      const expected = {
        newUrl: "http://example.com?key1=value1",
        queryString: "?key1=value1",
      };

      expect(constructHashURL(baseUrl, params)).toEqual(expected);
    });

    test("should remove exisiting parameters if they are updated to null", () => {
      const baseUrl = "http://example.com?key1=value1&key2=value2";
      const params = { key2: null };

      const expected = {
        newUrl: "http://example.com?key1=value1",
        queryString: "?key1=value1",
      };

      expect(constructHashURL(baseUrl, params)).toEqual(expected);
    });

    test("should not remove exisiting parameters if they are updated to falsy values", () => {
      const baseUrl = "http://example.com?key1=value1&key2=value2&key3=value3";
      const params = {
        key1: "",
        key2: false,
        key3: 0,
      };

      const expected = {
        newUrl: "http://example.com?key1=&key2=false&key3=0",
        queryString: "?key1=&key2=false&key3=0",
      };

      expect(constructHashURL(baseUrl, params)).toEqual(expected);
    });
  });
});

describe("makeRegExp", () => {
  test("should return RegExp correctly", () => {
    const value = "example";
    const expected = /example/iu;
    expect(makeRegExp(value)).toEqual(expected);
  });

  test("should handle special RegExp characters", () => {
    const value = "...";
    const expected = /\.\.\./iu;
    expect(makeRegExp(value)).toEqual(expected);
  });

  test("should throw error if value is not of type string", () => {
    const value = [];
    expect(() => {
      makeRegExp(value);
    }).toThrow();
  });
});

describe("decodeFilter", () => {
  test("should decode filter correctly", () => {
    const filter = "0_cputime_1";
    const expected = { tool: "0", name: "cputime", column: "1" };
    expect(decodeFilter(filter)).toEqual(expected);
  });

  test("should handle empty filters", () => {
    const filter = "__";
    const expected = { tool: "", name: "", column: "" };
    expect(decodeFilter(filter)).toEqual(expected);
  });

  test("should handle text id filters", () => {
    const filter = "id";
    const expected = { tool: "id", name: undefined, column: undefined };
    expect(decodeFilter(filter)).toEqual(expected);
  });

  test("should throw errors if there are is only one '_' in the filter id", () => {
    expect(() => decodeFilter("0cputime_")).toThrow();
    expect(() => decodeFilter("0_cputime2")).toThrow();
  });

  test("should decode correctly with more than two '_' in the filter id", () => {
    const filter = "0_cpu_time_1";
    const expected = { tool: "0", name: "cpu_time", column: "1" };
    expect(decodeFilter(filter)).toEqual(expected);
  });
});

describe("tokenizePart", () => {
  test("should tokenizePart to get Filter keys", () => {
    const string = "id_any(value(%29)),0(1*cputime*(value(2)))";
    const expected = { 0: "1*cputime*(value(2))", id_any: "value(%29)" };
    expect(tokenizePart(string)).toEqual(expected);
  });

  test("should tokenizePart to get Filter values", () => {
    const string = "value(%29)";
    const expected = { value: ")" };
    expect(tokenizePart(string, true)).toEqual(expected);
  });
});

describe("serialization", () => {
  let serializer;
  const statusValues = [
    [["true", "false", "TIMEOUT", "OOM", "false(reach)"]],
    [["true", "false", "TIMEOUT", "OOM", "false(reach)"]],
  ];
  const categoryValues = [
    [["correct ", "wrong ", "missing ", "unknown "]],
    [["correct ", "wrong ", "missing ", "unknown "]],
  ];

  const makeSelection = (selection, base) => {
    // the status column has id 0
    return base[0].filter((item) =>
      selection && selection.length > 0
        ? selection.every((select) => item !== select)
        : true,
    );
  };
  beforeEach(() => {
    serializer = makeFilterSerializer({
      statusValues,
      categoryValues,
    });
  });

  test("should serialize id filters", () => {
    const filter = [{ id: "id", values: ["abc", "def"] }];
    const expected = "id(values(abc,def))";

    expect(serializer(filter)).toBe(expected);
  });

  test("should serialize id filters with parentheses", () => {
    const filter = [{ id: "id", values: ["(", ")"] }];
    const expected = "id(values(%28,%29))";

    expect(serializer(filter)).toBe(expected);
  });

  test("should serialize id filter to escape special characters", () => {
    const filter = [{ id: "id", value: "?#&=(),*", isTableTabFilter: true }];
    const expected = "id_any(value(%3F%23%26%3D%28%29%2C*))";

    expect(serializer(filter)).toBe(expected);
  });

  test("should serialize id filter with one opening parentheses", () => {
    const filter = [{ id: "id", value: "(", isTableTabFilter: true }];
    const expected = "id_any(value(%28))";

    expect(serializer(filter)).toBe(expected);
  });

  test("should serialize id filter with one closing parentheses", () => {
    const filter = [{ id: "id", value: ")", isTableTabFilter: true }];
    const expected = "id_any(value(%29))";

    expect(serializer(filter)).toBe(expected);
  });

  test("should serialize normal value filters for one runset", () => {
    const filter = [
      { id: "0_cputime_1", value: "1223:4567" },
      { id: "0_hostname_2", value: "satu" },
    ];

    const urlencoded = encodeURIComponent("1223:4567");
    const expected = `0(1*cputime*(value(${urlencoded})),2*hostname*(value(satu)))`;

    expect(serializer(filter)).toBe(expected);
  });

  test("should serialize normal value filters in multiple runsets", () => {
    const filter = [
      { id: "0_cputime_1", value: "1223:4567" },
      { id: "1_cputime_1", value: ":4567" },
      { id: "0_hostname_2", value: "satu" },
      { id: "1_hostname_2", value: "tilo" },
    ];

    const urlencoded1 = encodeURIComponent("1223:4567");
    const urlencoded2 = encodeURIComponent(":4567");

    const filterRunset1 = `0(1*cputime*(value(${urlencoded1})),2*hostname*(value(satu)))`;
    const filterRunset2 = `1(1*cputime*(value(${urlencoded2})),2*hostname*(value(tilo)))`;
    const expected = `${filterRunset1},${filterRunset2}`;

    expect(serializer(filter)).toBe(expected);
  });

  test("should serialize normal value filters in multiple runsets and id filter", () => {
    const filter = [
      { id: "0_cputime_1", value: "1223:4567" },
      { id: "1_cputime_1", value: ":4567" },
      { id: "0_hostname_2", value: "satu" },
      { id: "1_hostname_2", value: "tilo" },
      { id: "id", values: ["abc", "def"] },
    ];

    const urlencoded1 = encodeURIComponent("1223:4567");
    const urlencoded2 = encodeURIComponent(":4567");

    const filterRunset1 = `0(1*cputime*(value(${urlencoded1})),2*hostname*(value(satu)))`;
    const filterRunset2 = `1(1*cputime*(value(${urlencoded2})),2*hostname*(value(tilo)))`;
    const expected = `id(values(abc,def)),${filterRunset1},${filterRunset2}`;

    expect(serializer(filter)).toBe(expected);
  });

  test("should serialize status filter correctly (notIn)", () => {
    const uncheckedBoxes = ["true", "false"];
    const selected = makeSelection(uncheckedBoxes, statusValues[0]);
    const standardCategories = makeSelection(null, categoryValues[0]);

    const filter = selected.map((status) => ({
      id: "0_status_0",
      value: status,
    }));
    filter.push(
      ...standardCategories.map((category) => ({
        id: "0_status_0",
        value: category,
      })),
    );

    const expected =
      "0(0*status*(status(notIn(true,false)),category(notIn())))";

    expect(serializer(filter)).toBe(expected);
  });

  test("should serialize status filter correctly (in)", () => {
    const uncheckedBoxes = ["true", "false", "TIMEOUT"];
    const selected = makeSelection(uncheckedBoxes, statusValues[0]);
    const standardCategories = makeSelection(null, categoryValues[0]);

    const filter = selected.map((status) => ({
      id: "0_status_0",
      value: status,
    }));
    filter.push(
      ...standardCategories.map((category) => ({
        id: "0_status_0",
        value: category,
      })),
    );

    const encoded = encodeURIComponent("false(reach)");

    const expected = `0(0*status*(status(in(OOM,${encoded})),category(notIn())))`;

    expect(serializer(filter)).toBe(expected);
  });

  test("should serialize status filter correctly in multiple runsets", () => {
    const uncheckedBoxes1 = ["true", "false", "TIMEOUT"];
    const uncheckedBoxes2 = ["true", "false"];
    const selected1 = makeSelection(uncheckedBoxes1, statusValues[0]);
    const selected2 = makeSelection(uncheckedBoxes2, statusValues[0]);
    const standardCategories = makeSelection(null, categoryValues[0]);

    const makeStatus = (selection, runset) =>
      selection.map((status) => ({
        id: `${runset}_status_0`,
        value: status,
      }));

    const filter = [...makeStatus(selected1, 0), ...makeStatus(selected2, 1)];

    filter.push(
      ...standardCategories.map((category) => ({
        id: "0_status_0",
        value: category,
      })),
    );

    filter.push(
      ...standardCategories.map((category) => ({
        id: "1_status_0",
        value: category,
      })),
    );

    const encoded = encodeURIComponent("false(reach)");

    const expected1 = `0(0*status*(status(in(OOM,${encoded})),category(notIn())))`;
    const expected2 = `1(0*status*(status(notIn(true,false)),category(notIn())))`;

    expect(serializer(filter)).toBe(`${expected1},${expected2}`);
  });

  test("should serialize category filter correctly (notIn)", () => {
    const uncheckedBoxes = ["unknown "];
    const selected = makeSelection(uncheckedBoxes, categoryValues[0]);

    const standardStatus = makeSelection(null, statusValues[0]);

    const filter = selected.map((status) => ({
      id: "0_status_0",
      value: status,
    }));

    filter.push(
      ...standardStatus.map((status) => ({
        id: "0_status_0",
        value: status,
      })),
    );

    const expected = "0(0*status*(status(notIn()),category(notIn(unknown))))";

    expect(serializer(filter)).toBe(expected);
  });

  test("should serialize category filter correctly (in)", () => {
    const uncheckedBoxes = ["correct ", "wrong "];
    const selected = makeSelection(uncheckedBoxes, categoryValues[0]);

    const standardStatus = makeSelection(null, statusValues[0]);

    const filter = selected.map((status) => ({
      id: "0_status_0",
      value: status,
    }));

    filter.push(
      ...standardStatus.map((status) => ({
        id: "0_status_0",
        value: status,
      })),
    );

    const expected = `0(0*status*(status(notIn()),category(in(missing,unknown))))`;

    expect(serializer(filter)).toBe(expected);
  });

  test("should serialize category filter correctly in multiple runsets", () => {
    const uncheckedBoxes1 = ["correct ", "wrong "];
    const uncheckedBoxes2 = ["unknown "];
    const selected1 = makeSelection(uncheckedBoxes1, categoryValues[0]);
    const selected2 = makeSelection(uncheckedBoxes2, categoryValues[0]);

    const standardStatus = makeSelection(null, statusValues[0]);

    const makeStatus = (selection, runset) =>
      selection.map((status) => ({
        id: `${runset}_status_0`,
        value: status,
      }));

    const filter = [...makeStatus(selected1, 0), ...makeStatus(selected2, 1)];

    filter.push(
      ...standardStatus.map((status) => ({
        id: "0_status_0",
        value: status,
      })),
    );

    filter.push(
      ...standardStatus.map((status) => ({
        id: "1_status_0",
        value: status,
      })),
    );

    const expected1 = `0(0*status*(status(notIn()),category(in(missing,unknown))))`;
    const expected2 = `1(0*status*(status(notIn()),category(notIn(unknown))))`;

    expect(serializer(filter)).toBe(`${expected1},${expected2}`);
  });

  test("should serialize category filter and status filter", () => {
    const uncheckedBoxes = ["correct ", "wrong "];
    const selected = makeSelection(uncheckedBoxes, categoryValues[0]);

    const filter = selected.map((category) => ({
      id: "0_status_0",
      value: category,
    }));
    filter.push({ id: "0_status_0", value: "true" });

    const expected = `0(0*status*(status(in(true)),category(in(missing,unknown))))`;

    expect(serializer(filter)).toBe(expected);
  });

  test("Should handle empty status filters", () => {
    const testStatusValues = [[["true", "false"]]];
    const testCategoryValues = [[["correct ", "wrong ", "missing "]]];

    const inp = [
      { id: "0_status_0", value: "wrong " },
      { id: "0_status_0", value: "missing " },
      { id: "id", values: Array(0) },
    ];

    const expected = "0(0*status*(status(empty()),category(notIn(correct))))";

    const testSerializer = makeFilterSerializer({
      statusValues: testStatusValues,
      categoryValues: testCategoryValues,
    });

    expect(testSerializer(inp)).toBe(expected);
  });

  test("Should handle empty category filters", () => {
    const testStatusValues = [[["true", "false"]]];
    const testCategoryValues = [[["correct ", "wrong ", "missing "]]];

    const inp = [
      { id: "0_status_0", value: "true" },
      { id: "id", values: Array(0) },
    ];

    const expected = "0(0*status*(status(in(true)),category(empty())))";

    const testSerializer = makeFilterSerializer({
      statusValues: testStatusValues,
      categoryValues: testCategoryValues,
    });

    expect(testSerializer(inp)).toBe(expected);
  });

  test("Should produce an empty status filter if all fields are selected", () => {
    const testStatusValues = [[["true", "false"]]];
    const testCategoryValues = [[["correct ", "wrong ", "missing "]]];

    const inp = [
      { id: "0_status_0", value: "true" },
      { id: "0_status_0", value: "false" },
      { id: "0_status_0", value: "correct " },
      { id: "0_status_0", value: "wrong " },
      { id: "0_status_0", value: "missing " },
      { id: "0_cputime_1", value: "1234" },
      { id: "id", values: Array(0) },
    ];

    const testSerializer = makeFilterSerializer({
      statusValues: testStatusValues,
      categoryValues: testCategoryValues,
    });

    const expected =
      "0(0*status*(status(notIn()),category(notIn())),1*cputime*(value(1234)))";

    expect(testSerializer(inp)).toEqual(expected);
  });
});

describe("Filter deserialization", () => {
  let deserializer;

  const statusValues = [
    [["true", "false", "TIMEOUT", "OOM", "false(reach)"]],
    [["true", "false", "TIMEOUT", "OOM", "false(reach)"]],
  ];
  const categoryValues = [
    [["correct ", "wrong ", "missing ", "unknown "]],
    [["correct ", "wrong ", "missing ", "unknown "]],
  ];

  const makeStandardStatusValues = (id) =>
    statusValues[0][0].map((value) => ({ id, value }));
  const makeStandardCategoryValues = (id) =>
    categoryValues[0][0].map((value) => ({ id, value }));

  beforeEach(() => {
    deserializer = makeFilterDeserializer({ statusValues, categoryValues });
  });

  test("should deserialize id filter", () => {
    const string = "id(values(abc,def))";

    const expected = [{ id: "id", values: ["abc", "def"] }];

    expect(deserializer(string)).toStrictEqual(expected);
  });

  test("should serialize id filters with parentheses", () => {
    const string = "id(values(%28,%29))";

    const expected = [{ id: "id", values: ["(", ")"] }];

    expect(deserializer(string)).toStrictEqual(expected);
  });

  test("should deserialize id filter with one opening parentheses", () => {
    const string = "id_any(value(%28))";

    const expected = [{ id: "id", value: "(", isTableTabFilter: true }];

    expect(deserializer(string)).toStrictEqual(expected);
  });

  test("should deserialize id filter with one closing parentheses", () => {
    const string = "id_any(value(%29))";

    const expected = [{ id: "id", value: ")", isTableTabFilter: true }];

    expect(deserializer(string)).toStrictEqual(expected);
  });

  test("should deserialize Table Tab Id filter with special characters", () => {
    const string = "id_any(value(%3F%23%26%3D()%2C*))*";

    const expected = [{ id: "id", value: "?#&=(),*", isTableTabFilter: true }];

    expect(deserializer(string)).toStrictEqual(expected);
  });

  test("should deserialize normal values for one runset", () => {
    const string = "0(1*cputime*(value(%3A1234)))";

    const expected = [{ id: "0_cputime_1", value: ":1234" }];

    expect(deserializer(string)).toStrictEqual(expected);
  });

  test("should deserialize normal values for many runsets", () => {
    const string =
      "0(1*cputime*(value(%3A1234))),1(1*cputime*(value(23%3A1234)))";

    const expected = [
      { id: "0_cputime_1", value: ":1234" },
      { id: "1_cputime_1", value: "23:1234" },
    ];

    expect(deserializer(string)).toStrictEqual(expected);
  });

  test("should deserialize status filters (in)", () => {
    const string = "0(0*status*(status(in(true,false))))";
    const defaultCategories = makeStandardCategoryValues("0_status_0");

    const expected = [
      { id: "0_status_0", value: "true" },
      { id: "0_status_0", value: "false" },
      ...defaultCategories,
    ];

    expect(deserializer(string)).toStrictEqual(expected);
  });

  test("should deserialize status filters (notIn)", () => {
    const string = "0(0*status*(status(notIn(true,false))))";
    const defaultCategories = makeStandardCategoryValues("0_status_0");

    const expected = [
      { id: "0_status_0", value: "TIMEOUT" },
      { id: "0_status_0", value: "OOM" },
      { id: "0_status_0", value: "false(reach)" },
      ...defaultCategories,
    ];

    expect(deserializer(string)).toStrictEqual(expected);
  });

  test("should deserialize status filters in multiple runsets", () => {
    const string =
      "0(0*status*(status(in(true,false)))),1(0*status*(status(notIn(true,false))))";
    const defaultCategories0 = makeStandardCategoryValues("0_status_0");
    const defaultCategories1 = makeStandardCategoryValues("1_status_0");

    const expected = [
      { id: "0_status_0", value: "true" },
      { id: "0_status_0", value: "false" },
      ...defaultCategories0,
      { id: "1_status_0", value: "TIMEOUT" },
      { id: "1_status_0", value: "OOM" },
      { id: "1_status_0", value: "false(reach)" },
      ...defaultCategories1,
    ];

    expect(deserializer(string)).toStrictEqual(expected);
  });
  // categories

  test("should deserialize category filters (in)", () => {
    const string = "0(0*status*(category(in(correct,wrong))))";
    const defaultStatus = makeStandardStatusValues("0_status_0");

    const expected = [
      { id: "0_status_0", value: "correct " },
      { id: "0_status_0", value: "wrong " },
      ...defaultStatus,
    ];

    expect(deserializer(string)).toStrictEqual(expected);
  });

  test("should deserialize category filters (notIn)", () => {
    const string = "0(0*status*(category(notIn(correct,wrong))))";
    const defaultStatus = makeStandardStatusValues("0_status_0");

    const expected = [
      { id: "0_status_0", value: "missing " },
      { id: "0_status_0", value: "unknown " },
      ...defaultStatus,
    ];

    expect(deserializer(string)).toStrictEqual(expected);
  });

  test("should deserialize category filters in multiple runsets", () => {
    const string =
      "0(0*status*(category(in(correct,wrong)))),1(0*status*(category(notIn(correct,wrong))))";

    const defaultStatus0 = makeStandardStatusValues("0_status_0");
    const defaultStatus1 = makeStandardStatusValues("1_status_0");

    const expected = [
      { id: "0_status_0", value: "correct " },
      { id: "0_status_0", value: "wrong " },
      ...defaultStatus0,
      { id: "1_status_0", value: "missing " },
      { id: "1_status_0", value: "unknown " },
      ...defaultStatus1,
    ];

    expect(deserializer(string)).toStrictEqual(expected);
  });

  test("should handle empty category filters correctly", () => {
    const string = "0(0*status*(category(empty()),status(in(true))))";

    const expected = [{ id: "0_status_0", value: "true" }];

    expect(deserializer(string)).toStrictEqual(expected);
  });

  test("should handle empty status filters correctly", () => {
    const string = "0(0*status*(category(in(missing)),status(empty())))";

    const expected = [{ id: "0_status_0", value: "missing " }];

    expect(deserializer(string)).toStrictEqual(expected);
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
    builder.addDataItem("0.02345");

    const formatter = builder.build();

    // we have 4 digits before and 5 digits after the decimal point
    const number1 = "23";
    const number2 = "23.1";
    const number3 = "0.123";
    const number4 = "0.01337";

    const expected1 = "23      ";
    const expected2 = "23.1    ";
    const expected3 = "0.123  ";
    const expected4 = "0.01337";

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
    builder.addDataItem("0.02345");

    const formatter = builder.build();

    // we have 4 digits before and 5 digits after the decimal point
    const number1 = "23";
    const number2 = "23.1";
    const number3 = "0.123";
    const number4 = "0.01337";

    const expected1 = "23&#x2008;     ".replace(/ /g, "&#x2007;");
    const expected2 = "23.1    ".replace(/ /g, "&#x2007;");
    const expected3 = "0.123  ".replace(/ /g, "&#x2007;");
    const expected4 = "0.01337".replace(/ /g, "&#x2007;");

    const actual1 = formatter(number1, { whitespaceFormat: true, html: true });
    const actual2 = formatter(number2, { whitespaceFormat: true, html: true });
    const actual3 = formatter(number3, { whitespaceFormat: true, html: true });
    const actual4 = formatter(number4, { whitespaceFormat: true, html: true });

    expect(actual1).toBe(expected1);
    expect(actual2).toBe(expected2);
    expect(actual3).toBe(expected3);
    expect(actual4).toBe(expected4);
  });

  test("should correctly round very precise numbers", () => {
    const num = 0.010974345997965429;
    const nBuilder = new NumberFormatterBuilder(3);

    expect(nBuilder.build()(num)).toBe("0.0110");
  });

  test("should handle 0 correctly", () => {
    const num = 0;

    const formatter = builder.build();
    const actual = formatter(num, { leadingZero: true });

    expect(actual).toBe("0");
  });

  test("should handle rounding up to the first decimal digit", () => {
    const num = 2.1968865394592285;

    const b = new NumberFormatterBuilder(3);
    const formatter = b.build();
    const actual = formatter(num, { leadingZero: true });

    expect(actual).toBe("2.20");
  });

  test("should handle rounding up with integer carry", () => {
    const num = 10.960994243621826;

    const b = new NumberFormatterBuilder(3);
    const formatter = b.build();

    const actual = formatter(num, { leadingZero: true });

    expect(actual).toBe("11.0");
  });

  test("handle carry in very precise numbers", () => {
    const num = 0.013950547000604274;

    const b = new NumberFormatterBuilder(2);
    const formatter = b.build();

    const actual = formatter(num, { leadingZero: true });

    expect(actual).toBe("0.014");
  });

  test("should correctly round number with one integer digit", () => {
    const num = 2.0000001;

    const b = new NumberFormatterBuilder(4);
    const formatter = b.build();

    const actual = formatter(num, { leadingZero: true });

    expect(actual).toBe("2.000");
  });

  test("should correctly handle numbers in scientific notation with a decimal coefficient", () => {
    const num = 2.2e-7;

    const b = new NumberFormatterBuilder(2);
    const formatter = b.build();

    const actual = formatter(num, { leadingZero: true });

    expect(actual).toBe("0.00000022");
  });
  test("should correctly handle numbers in scientific notation with a integer coeffecient", () => {
    const num = 2e-7;

    const b = new NumberFormatterBuilder(2);
    const formatter = b.build();

    const actual = formatter(num, { leadingZero: true });

    expect(actual).toBe("0.0000002");
  });

  test("should not insert unnecessary decimal spacings", () => {
    const num = 2.0;

    const b = new NumberFormatterBuilder(1);
    b.addDataItem(num);
    const formatter = b.build();

    const actual = formatter(num, { whitespaceFormat: true, html: true });

    expect(actual).toBe("2");
  });

  test("decimal spacings should not count towards number of character spacings", () => {
    const num = 2.0;

    const b = new NumberFormatterBuilder(3);
    b.addDataItem(2.01);
    const formatter = b.build();

    const actual = formatter(num, { whitespaceFormat: true, html: true });

    expect(actual).toBe("2&#x2008;&#x2007;&#x2007;");
  });

  test("Should be able to deal with JS rounding errors", () => {
    const num = 7.1994551950000005;

    const b = new NumberFormatterBuilder(3);
    b.addDataItem(2.01);
    const formatter = b.build();

    const actual = formatter(num);

    // As the rounding of the last digits results in a carry-over,
    // we end up with the addition of 7.1 and 0.1
    // In JS 7.1 + 0.1 evaluates to 7.199999999999999, which caused an issue
    expect(actual).toBe("7.20");
  });

  test("Should always render 0 when resulting value resolves to a Number representation of 0", () => {
    const num = 0;

    const b = new NumberFormatterBuilder(3);
    b.addDataItem(0.001);
    const formatter = b.build();

    const actual = formatter(num, {
      whitespaceFormat: true,
      html: true,
      leadingZero: false,
    });

    expect(actual).toBe(
      "0.   ".replace(".", "&#x2008;").replace(/ /g, "&#x2007;"),
    );
  });

  describe("additionalFormatting function", () => {
    test("Should correctly pass number of significant digits in context", async () => {
      let resolve;

      const promise = new Promise((res) => {
        resolve = res;
      });

      const additionalFormatting = (_, context) => {
        expect(context.significantDigits).toBe(9);
        resolve();
      };

      const b = new NumberFormatterBuilder(9);
      const formatter = b.build();

      formatter(0, { additionalFormatting });

      await promise;
    });

    test("Should correctly pass max length of decimals of input", async () => {
      let resolve;

      const promise = new Promise((res) => {
        resolve = res;
      });

      const additionalFormatting = (_, context) => {
        expect(context.maxDecimalInputLength).toBe(4);
        resolve();
      };

      const b = new NumberFormatterBuilder(9);
      b.addDataItem(1);
      b.addDataItem(1.23);
      b.addDataItem(1.2345);
      b.addDataItem(1.234);
      const formatter = b.build();

      formatter(0, { additionalFormatting });

      await promise;
    });
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

describe("splitUrlPathForMatchingPrefix", () => {
  test("should work if both URLs are equal", () => {
    const a = new URL("file:///home/foo/bar.html");
    expect(splitUrlPathForMatchingPrefix(a, a)).toStrictEqual([
      "/home/foo",
      "bar.html",
    ]);
  });
  test("should work if first URL ends with slash", () => {
    const a = new URL("file:///home/foo/");
    const b = new URL("file:///home/foo");
    expect(splitUrlPathForMatchingPrefix(a, b)).toStrictEqual([
      "/home/foo",
      "",
    ]);
  });
  test("should work if first URL starts with second URL (terminating slash)", () => {
    const a = new URL("file:///home/foo/bar.html");
    const b = new URL("file:///home/foo");
    expect(splitUrlPathForMatchingPrefix(a, b)).toStrictEqual([
      "/home/foo",
      "bar.html",
    ]);
  });
  test("should work if first URL starts with second URL (terminating slash)", () => {
    const a = new URL("file:///home/foo/bar.html");
    const b = new URL("file:///home/foo/");
    expect(splitUrlPathForMatchingPrefix(a, b)).toStrictEqual([
      "/home/foo",
      "bar.html",
    ]);
  });
  test("should work if second URL starts with first URL", () => {
    const a = new URL("file:///home/foo/bar.html");
    const b = new URL("file:///home/foo/bar.html/test");
    expect(splitUrlPathForMatchingPrefix(a, b)).toStrictEqual([
      "/home/foo",
      "bar.html",
    ]);
  });
  test("should work for Windows paths", () => {
    const a = new URL("file:///C:/foo/bar.html");
    const b = new URL("file:///C:/foo/bar2.html");
    expect(splitUrlPathForMatchingPrefix(a, b)).toStrictEqual([
      "/C:/foo",
      "bar.html",
    ]);
  });
  test("should work for Windows paths in different directories", () => {
    const a = new URL("file:///C:/foo/bar.html");
    const b = new URL("file:///C:/bar/bar.html");
    expect(splitUrlPathForMatchingPrefix(a, b)).toStrictEqual([
      "/C:",
      "foo/bar.html",
    ]);
  });
  test("should produce empty prefix for paths on different partitions", () => {
    const a = new URL("file:///C:/foo/bar.html");
    const b = new URL("file:///D:/foo/bar.html");
    expect(splitUrlPathForMatchingPrefix(a, b)).toStrictEqual([
      "",
      "C:/foo/bar.html",
    ]);
  });
  test("should produce empty prefix for paths in different subdirectories of /", () => {
    const a = new URL("file:///home/bar.html");
    const b = new URL("file:///tmp/bar.html");
    expect(splitUrlPathForMatchingPrefix(a, b)).toStrictEqual([
      "",
      "home/bar.html",
    ]);
  });
});
