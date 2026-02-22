// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import {
  isNil,
  getRawOrDefault,
  omit,
  isNumericColumn,
  decodeFilter,
  makeRegExp,
} from "./utils";
import type {
  FilterTableRow as TableRow,
  Dataset,
  FilterUIItem as FilterItem,
  ColumnFilter,
  ToolMatcher,
  Matcher,
  IntermediateStatusColumn,
  IntermediateTextColumn,
  IntermediateNumericColumn,
  IntermediateColumn,
} from "../types/filters";

const asRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null;

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
const getFilterableData = ({ tools, rows }: Dataset) => {
  const mapped = tools.map((tool, idx) => {
    let statusIdx: number | undefined;
    const { tool: toolName, date, niceName } = tool;
    const name = `${toolName} ${date} ${niceName}`;

    const columns = tool.columns.map(
      (col, colIdx): IntermediateColumn | undefined => {
        if (!col) {
          return undefined;
        }
        if (col.type === "status") {
          statusIdx = colIdx;
          return {
            ...col,
            type: "status",
            categories: {},
            statuses: {},
            idx: colIdx,
          };
        }
        if (col.type === "text") {
          return {
            ...col,
            type: "text",
            distincts: {},
            idx: colIdx,
          };
        }
        return {
          ...col,
          min: Infinity,
          max: -Infinity,
          idx: colIdx,
        };
      },
    );

    if (!isNil(statusIdx)) {
      const current = columns[statusIdx];
      if (current && current.type === "status") {
        columns[statusIdx] = {
          ...current,
          categories: {},
          statuses: {},
        };
      }
    }

    rows.forEach((row) => {
      const result = row.results[idx];
      // convention as of writing this commit is to postfix categories with a space character
      if (!isNil(statusIdx)) {
        const statusCol = columns[statusIdx] as
          | IntermediateStatusColumn
          | undefined;
        if (statusCol) {
          statusCol.categories[`${result.category} `] = true;
        }
      }

      result.values.forEach((col, colIdx) => {
        const { raw } = col;
        const filterCol = columns[colIdx];
        if (!filterCol || isNil(raw)) {
          return;
        }

        if (filterCol.type === "status") {
          (filterCol as IntermediateStatusColumn).statuses[String(raw)] = true;
        } else if (filterCol.type === "text") {
          (filterCol as IntermediateTextColumn).distincts[String(raw)] = true;
        } else if ("min" in filterCol && "max" in filterCol) {
          const numCol = filterCol as IntermediateNumericColumn;
          numCol.min = Math.min(numCol.min, Number(raw));
          numCol.max = Math.max(numCol.max, Number(raw));
        }
      });
    });

    return {
      name,
      columns: columns.map((c) => {
        if (!c) {
          return undefined;
        }

        const { idx: _idx, ...rest } = c;

        if (c.type === "status") {
          const statusCol = c as IntermediateStatusColumn;
          const { categories, statuses, ...restOfCol } = statusCol;
          void restOfCol;
          return {
            ...rest,
            categories: Object.keys(categories),
            statuses: Object.keys(statuses),
          };
        }
        if (c.type === "text") {
          const textCol = c as IntermediateTextColumn;
          const { distincts, ...restOfCol } = textCol;
          void restOfCol;
          return {
            ...rest,
            distincts: Object.keys(distincts),
          };
        }
        return rest;
      }),
    };
  });
  return mapped;
};

const applyNumericFilter = (
  filter: { id: string; value: string },
  row: Record<string, unknown>,
) => {
  const raw = getRawOrDefault(row[filter.id] as unknown, undefined);
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
    return String(raw).startsWith(filterParams[0]);
  }
  return false;
};

const applyTextFilter = (
  filter: { id: string; value: string },
  row: Record<string, unknown>,
) => {
  const raw = getRawOrDefault(row[filter.id] as unknown, undefined);
  if (raw === undefined) {
    // empty cells never match
    return;
  }
  return String(raw).includes(filter.value);
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
const buildMatcher = (filters: FilterItem[]) => {
  const out = filters.reduce<Matcher>((acc, { id, value, type, values }) => {
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

    const { tool, column: columnIdx } = decodeFilter(id);
    const columnKey = String(columnIdx ?? "");

    if (value === "diff") {
      // this branch is noop as of now
      if (!acc.diff) {
        acc.diff = [];
      }
      acc.diff.push({ col: columnKey });
      return acc;
    }

    if (!acc[tool]) {
      acc[tool] = {};
    }

    let filter: ColumnFilter;
    if (
      typeof value === "string" &&
      isNumericColumn({ type }) &&
      value.includes(":")
    ) {
      const [minV, maxV] = value.split(":");
      const min = minV === "" ? -Infinity : Number(minV);
      const max = maxV === "" ? Infinity : Number(maxV);
      filter = { min, max };
    } else {
      const v = String(value ?? "");
      if (v[v.length - 1] === " ") {
        filter = { category: v.substr(0, v.length - 1) };
      } else if (type === "status") {
        filter = { status: v };
      } else {
        filter = { value: v };
      }
    }

    const toolBucket = acc[tool] as ToolMatcher;
    if (!toolBucket[columnKey]) {
      toolBucket[columnKey] = [];
    }
    toolBucket[columnKey].push(filter);

    return acc;
  }, {} as Matcher);

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
const applyMatcher = (matcher: Matcher) => (data: TableRow[]) => {
  let diffd = [...data];

  if (matcher.diff) {
    diffd = diffd.filter((row) => {
      for (const { col } of matcher.diff ?? []) {
        const colIdx = Number(col);
        const vals: Record<string, true> = {};
        for (const tool of row.results) {
          const val = tool.values[colIdx]?.raw;
          const key = String(val);
          if (!vals[key]) {
            vals[key] = true;
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
    const { value: idValue, values: idValues } = matcher.id ?? {};
    if (idValue) {
      // pre computing RegExp of idValue after excaping the special characters
      const regexToCompare = makeRegExp(idValue);
      diffd = diffd.filter(({ id }) =>
        id.some((idName) => idName === idValue || regexToCompare.test(idName)),
      );
    } else if (Array.isArray(idValues)) {
      // pre computing RegExp of each element of idValues array after excaping the special characters
      const idValuesWithRegex = idValues.map((filterValue) => ({
        filterRegex: makeRegExp(filterValue),
        filterValue,
      }));

      diffd = diffd.filter(({ id }) =>
        idValuesWithRegex.every(({ filterRegex, filterValue }, idx) => {
          const idName = id[idx];
          if (isNil(filterValue) || filterValue === "") {
            return true;
          }
          if (isNil(idName) || idName === "") {
            return false;
          }
          return idName === filterValue || filterRegex.test(idName);
        }),
      );
    }
  }

  const toolsOnly = omit(["diff", "id"], matcher) as Record<string, unknown>;
  const out = diffd.filter((row) => {
    for (const toolKey in toolsOnly) {
      const toolMatcher = toolsOnly[toolKey];
      if (!asRecord(toolMatcher)) {
        continue;
      }

      const toolIdx = Number(toolKey);

      for (const columnKey in toolMatcher) {
        let columnPass = false;
        let categoryPass = false;
        let statusPass = false;

        const columnFilters = toolMatcher[columnKey];
        if (!Array.isArray(columnFilters)) {
          continue;
        }

        const columnIdx = Number(columnKey);

        for (const filter of columnFilters) {
          if ("min" in filter && "max" in filter) {
            const rawValue = row.results[toolIdx]?.values[columnIdx]?.raw;
            if (isNil(rawValue)) {
              columnPass = false;
              continue;
            }
            const num = Number(rawValue);
            columnPass = columnPass || (num >= filter.min && num <= filter.max);
          } else if ("category" in filter) {
            categoryPass =
              row.results[toolIdx]?.category === String(filter.category) ||
              categoryPass;
            columnPass = categoryPass && statusPass;
          } else if ("status" in filter) {
            const emptyRowPass =
              row.results[toolIdx]?.category === "empty" &&
              String(filter.status) === statusForEmptyRows;
            statusPass =
              row.results[toolIdx]?.values[columnIdx]?.raw === filter.status ||
              statusPass ||
              emptyRowPass;
            columnPass = categoryPass && statusPass;
          } else if ("value" in filter) {
            const rawValue = row.results[toolIdx]?.values[columnIdx]?.raw;
            if (isNil(rawValue)) {
              columnPass = false;
              continue;
            }
            const rawStr = String(rawValue);
            columnPass =
              columnPass ||
              String(filter.value) === rawStr ||
              rawStr.includes(String(filter.value));
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
