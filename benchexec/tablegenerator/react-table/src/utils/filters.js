// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import { isNil, getRawOrDefault, omit, isNumericColumn } from "./utils";
/* Status that will be used to identify whether empty rows should be shown. Currently,
   filtering for either categories or statuses creates filters for the other one as well.
   Since empty rows don't have a status, they will be filtered out all the time.
   To prevent this, this status placeholder will be used to indicate that empty rows
   should pass the status filtering. */
const statusForEmptyRows = "empty_row";

/**
 * Prepares raw data for filtering by retrieving available distinct values as min
 * and max values of numeric fields
 *
 * @param {Object} data -  Data object received from json data
 */
const getFilterableData = ({ tools, rows }) => {
  const mapped = tools.map((tool, idx) => {
    let statusIdx;
    const { tool: toolName, date, niceName } = tool;
    let name = `${toolName} ${date} ${niceName}`;
    const columns = tool.columns.map((col, idx) => {
      if (!col) {
        return undefined;
      }
      if (col.type === "status") {
        statusIdx = idx;
        return { ...col, categories: {}, statuses: {}, idx };
      }
      if (col.type === "text") {
        return { ...col, distincts: {}, idx };
      }
      return { ...col, min: Infinity, max: -Infinity, idx };
    });

    if (!isNil(statusIdx)) {
      columns[statusIdx] = {
        ...columns[statusIdx],
        categories: {},
        statuses: {},
      };
    }

    for (const row of rows) {
      const result = row.results[idx];
      // convention as of writing this commit is to postfix categories with a space character
      if (!isNil(statusIdx)) {
        columns[statusIdx].categories[`${result.category} `] = true;
      }

      for (const colIdx in result.values) {
        const col = result.values[colIdx];
        const { raw } = col;
        const filterCol = columns[colIdx];
        if (!filterCol || isNil(raw)) {
          continue;
        }

        if (filterCol.type === "status") {
          filterCol.statuses[raw] = true;
        } else if (filterCol.type === "text") {
          filterCol.distincts[raw] = true;
        } else {
          filterCol.min = Math.min(filterCol.min, Number(raw));
          filterCol.max = Math.max(filterCol.max, Number(raw));
        }
      }
    }

    return {
      name,
      columns: columns.map(({ distincts, categories, statuses, ...col }) => {
        if (distincts) {
          return { ...col, distincts: Object.keys(distincts) };
        }
        if (categories) {
          return {
            ...col,
            categories: Object.keys(categories),
            statuses: Object.keys(statuses),
          };
        }
        return col;
      }),
    };
  });
  return mapped;
};

const applyNumericFilter = (filter, row, cell) => {
  const raw = getRawOrDefault(row[filter.id]);
  if (raw === undefined) {
    // empty cells never match
    return;
  }
  const filterParams = filter.value.split(":");

  if (filterParams.length === 2) {
    const [start, end] = filterParams;

    const numRaw = Number(raw);
    const numStart = start ? Number(start) : -Infinity;
    const numEnd = end ? Number(end) : Infinity;

    return numRaw >= numStart && numRaw <= numEnd;
  }

  if (filterParams.length === 1) {
    return raw.startsWith(filterParams[0]);
  }
  return false;
};
const applyTextFilter = (filter, row, cell) => {
  const raw = getRawOrDefault(row[filter.id]);
  if (raw === undefined) {
    // empty cells never match
    return;
  }
  return raw.includes(filter.value);
};

/**
 * Transforms a list of filter objects into a matcher.
 * The matcher helps with data access and provides clear, parsed information
 * on what the filter should do.
 *
 * for example:
 *
 * Filter object: [
 *    {id: "0_status_1", value: "false"},
 *    {id: "0_status_1", value: "TIMEOUT"},
 *    {id: "0_cputime_3", value: "50: 1337"},
 * ]
 *
 * matcher: {
 *  0: {
 *      1: [{value: "false"}, {value: "TIMEOUT"}],   // all values on this level are disjunctively connected
 *      3: [{min: 50, max: 1337}],
 *    }
 * }
 *
 * @param {Array<Object>} filters - List of filters
 */
const buildMatcher = (filters) => {
  const out = filters.reduce((acc, { id, value, type, values }) => {
    if (
      (isNil(value) && isNil(values)) ||
      (typeof value === "string" && value.trim() === "all")
    ) {
      return acc;
    }
    if (id === "id") {
      acc.id = { value, values };
      return acc;
    }
    const [tool, , columnIdx] = id.split("_");
    if (value === "diff") {
      // this branch is noop as of now
      if (!acc.diff) {
        acc.diff = [];
      }
      acc.diff.push({ col: columnIdx });
      return acc;
    }
    if (!acc[tool]) {
      acc[tool] = {};
    }
    let filter;
    if (isNumericColumn({ type }) && value.includes(":")) {
      let [minV, maxV] = value.split(":");
      minV = minV === "" ? -Infinity : Number(minV);
      maxV = maxV === "" ? Infinity : Number(maxV);
      filter = { min: minV, max: maxV };
    } else {
      if (value[value.length - 1] === " ") {
        filter = { category: value.substr(0, value.length - 1) };
      } else if (type === "status") {
        filter = { status: value };
      } else {
        filter = { value };
      }
    }
    if (!acc[tool][columnIdx]) {
      acc[tool][columnIdx] = [];
    }
    acc[tool][columnIdx].push(filter);
    return acc;
  }, {});
  return out;
};

/**
 * @typedef (function(Object[])) MatchingFunction
 * @param {Object[]} data - the data of the current Table context
 * @returns {Object[]} filtered data
 */

/**
 *
 * @param {matcher} matcher - the pre-compiled matcher
 * @returns {MatchingFunction} - the built matching function. It requires
 */
const applyMatcher = (matcher) => (data) => {
  let diffd = [...data];
  if (matcher.diff) {
    diffd = diffd.filter((row) => {
      for (const { col } of matcher.diff) {
        const vals = {};
        for (const tool of row.results) {
          const val = tool.values[col].raw;
          if (!vals[val]) {
            vals[val] = true;
          }
        }
        if (Object.keys(vals).length === 1) {
          return false;
        }
      }
      return true;
    });
  }
  if (!isNil(matcher.id)) {
    const { value: idValue, values: idValues } = matcher.id;
    if (idValue) {
      diffd = diffd.filter(({ id }) =>
        id.some((idName) => idName === idValue || idName.includes(idValue)),
      );
    } else {
      diffd = diffd.filter(({ id }) =>
        idValues.every((filterValue, idx) => {
          const idName = id[idx];
          if (isNil(filterValue) || filterValue === "") {
            return true;
          }
          if (isNil(idName) || idName === "") {
            return false;
          }
          return idName === filterValue || idName.includes(filterValue);
        }),
      );
    }
  }
  const out = diffd.filter((row) => {
    for (const tool in omit(["diff", "id"], matcher)) {
      for (const column in matcher[tool]) {
        let columnPass = false;
        let categoryPass = false;
        let statusPass = false;
        for (const filter of matcher[tool][column]) {
          const { value, min, max, category, status } = filter;

          if (!isNil(min) && !isNil(max)) {
            const rawValue = row.results[tool].values[column].raw;
            if (isNil(rawValue)) {
              columnPass = false;
              continue;
            }
            const num = Number(rawValue);
            columnPass = columnPass || (num >= min && num <= max);
          } else if (!isNil(category)) {
            categoryPass =
              row.results[tool].category === category || categoryPass;
            columnPass = categoryPass && statusPass;
          } else if (!isNil(status)) {
            const emptyRowPass =
              row.results[tool].category === "empty" &&
              status === statusForEmptyRows;
            statusPass =
              row.results[tool].values[column].raw === status ||
              statusPass ||
              emptyRowPass;
            columnPass = categoryPass && statusPass;
          } else {
            const rawValue = row.results[tool].values[column].raw;
            if (isNil(rawValue)) {
              columnPass = false;
              continue;
            }
            columnPass =
              columnPass || value === rawValue || rawValue.includes(value);
          }

          if (columnPass) {
            // as multiple values of the same column are OR connected,
            // we can abort if we pass since the result will always be true.
            break;
          }
        }
        if (!columnPass) {
          // values of the same column are OR connected
          // multiple columns in the same row are AND connected
          // if the matcher fails for one column, the whole row fails
          return false;
        }
      }
    }
    // all filter requirements were satisfied
    return true;
  });
  return out;
};

export {
  getFilterableData,
  applyNumericFilter,
  applyTextFilter,
  applyMatcher,
  buildMatcher,
  statusForEmptyRows,
};
