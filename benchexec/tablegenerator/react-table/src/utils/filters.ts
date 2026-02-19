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

/* ============================================================
 * Types: Input data shapes
 * ============================================================ */

type RawCell = {
  raw?: string | number | null;
};

type TableRowResult = {
  category: string;
  values: RawCell[];
};

type TableRow = {
  id: string[];
  results: TableRowResult[];
};

type ToolColumn = {
  type?: string;
  title: string;
  [key: string]: unknown;
};

type Tool = {
  tool: string;
  date: string;
  niceName: string;
  columns: Array<ToolColumn | undefined>;
};

type Dataset = {
  tools: Tool[];
  rows: TableRow[];
};

/* ============================================================
 * Types: Filter UI input
 * ============================================================ */

type FilterItem = {
  id: string;
  value?: string;
  type?: string;
  values?: string[];
};

/* ============================================================
 * Types: Matcher (compiled filters)
 * ============================================================ */

type IdMatcher = {
  value?: string;
  values?: string[];
};

type DiffMatcherItem = {
  col?: string;
};

type NumericRangeFilter = {
  min: number;
  max: number;
};

type CategoryFilter = {
  category: string;
};

type StatusFilter = {
  status: string;
};

type TextValueFilter = {
  value: string;
};

type ColumnFilter =
  | NumericRangeFilter
  | CategoryFilter
  | StatusFilter
  | TextValueFilter;

type ToolMatcher = Record<string, ColumnFilter[]>;

type Matcher = {
  id?: IdMatcher;
  diff?: DiffMatcherItem[];
} & Record<string, ToolMatcher | IdMatcher | DiffMatcherItem[] | undefined>;

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

    const columns = tool.columns.map((col, colIdx) => {
      if (!col) {
        return undefined;
      }
      if (col.type === "status") {
        statusIdx = colIdx;
        return {
          ...col,
          categories: {} as Record<string, true>,
          statuses: {} as Record<string, true>,
          idx: colIdx,
        };
      }
      if (col.type === "text") {
        return { ...col, distincts: {} as Record<string, true>, idx: colIdx };
      }
      return { ...col, min: Infinity, max: -Infinity, idx: colIdx };
    });

    if (!isNil(statusIdx)) {
      const current = columns[statusIdx];
      if (current) {
        // NOTE (JS->TS): Added defensive check because columns entries may be undefined.
        columns[statusIdx] = {
          ...current,
          categories: {} as Record<string, true>,
          statuses: {} as Record<string, true>,
        };
      }
    }

    for (const row of rows) {
      const result = row.results[idx];
      // convention as of writing this commit is to postfix categories with a space character
      if (!isNil(statusIdx)) {
        const statusCol = columns[statusIdx];
        if (statusCol && "categories" in statusCol) {
          (statusCol.categories as Record<string, true>)[
            `${result.category} `
          ] = true;
        }
      }

      for (const colIdxStr in result.values) {
        // NOTE (JS->TS): Convert for..in string keys to numbers for safe array indexing.
        const colIdx = Number(colIdxStr);

        const col = result.values[colIdx];
        const { raw } = col;
        const filterCol = columns[colIdx];
        if (!filterCol || isNil(raw)) {
          continue;
        }

        if (filterCol.type === "status") {
          (filterCol as { statuses: Record<string, true> }).statuses[
            String(raw)
          ] = true;
        } else if (filterCol.type === "text") {
          (filterCol as { distincts: Record<string, true> }).distincts[
            String(raw)
          ] = true;
        } else {
          (filterCol as { min: number; max: number }).min = Math.min(
            (filterCol as { min: number }).min,
            Number(raw),
          );
          (filterCol as { min: number; max: number }).max = Math.max(
            (filterCol as { max: number }).max,
            Number(raw),
          );
        }
      }
    }

    return {
      name,
      columns: columns.map((c) => {
        if (!c) {
          return undefined;
        }

        const colRec = c as Record<string, unknown>;
        const distincts = colRec.distincts as Record<string, true> | undefined;
        const categories = colRec.categories as
          | Record<string, true>
          | undefined;
        const statuses = colRec.statuses as Record<string, true> | undefined;

        const rest = { ...colRec };

        // NOTE (JS->TS): Explicitly remove internal aggregation fields instead of
        // using unused destructuring bindings to satisfy ESLint no-unused-vars rule.
        delete (rest as Record<string, unknown>).distincts;
        delete (rest as Record<string, unknown>).categories;
        delete (rest as Record<string, unknown>).statuses;

        if (distincts) {
          return { ...rest, distincts: Object.keys(distincts) };
        }
        if (categories) {
          return {
            ...rest,
            categories: Object.keys(categories),
            statuses: Object.keys(statuses ?? {}),
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
  cell: unknown,
) => {
  void cell;

  // NOTE (JS->TS): Pass explicit default value for compatibility with typed signature.
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
    // NOTE (JS->TS): Cast raw to string for safe string operations because raw may be non-string at runtime.
    return String(raw).startsWith(filterParams[0]);
  }
  return false;
};

const applyTextFilter = (
  filter: { id: string; value: string },
  row: Record<string, unknown>,
  cell: unknown,
) => {
  void cell;

  // NOTE (JS->TS): Pass explicit default value for compatibility with typed signature.
  const raw = getRawOrDefault(row[filter.id] as unknown, undefined);
  if (raw === undefined) {
    // empty cells never match
    return;
  }
  // NOTE (JS->TS): Cast raw to string for safe string operations because raw may be non-string at runtime.
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
    // NOTE (JS->TS): Normalize possibly undefined decodeFilter output to a string key for dynamic matcher buckets.
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
      // NOTE (JS->TS): Added defensive runtime check because matcher buckets are dynamic and typed as unknown.
      if (!asRecord(toolMatcher)) {
        continue;
      }

      // NOTE (JS->TS): Convert dynamic tool keys to numbers for safe array indexing.
      const toolIdx = Number(toolKey);

      for (const columnKey in toolMatcher) {
        let columnPass = false;
        let categoryPass = false;
        let statusPass = false;

        const columnFilters = toolMatcher[columnKey];
        if (!Array.isArray(columnFilters)) {
          continue;
        }

        // NOTE (JS->TS): Convert dynamic column keys to numbers for safe array indexing.
        const columnIdx = Number(columnKey);

        for (const filter of columnFilters) {
          if (!asRecord(filter)) {
            continue;
          }

          const value = filter.value;
          const min = filter.min;
          const max = filter.max;
          const category = filter.category;
          const status = filter.status;

          if (!isNil(min) && !isNil(max)) {
            const rawValue = row.results[toolIdx]?.values[columnIdx]?.raw;
            if (isNil(rawValue)) {
              columnPass = false;
              continue;
            }
            const num = Number(rawValue);
            columnPass =
              columnPass || (num >= Number(min) && num <= Number(max));
          } else if (!isNil(category)) {
            categoryPass =
              row.results[toolIdx]?.category === String(category) ||
              categoryPass;
            columnPass = categoryPass && statusPass;
          } else if (!isNil(status)) {
            const emptyRowPass =
              row.results[toolIdx]?.category === "empty" &&
              String(status) === statusForEmptyRows;
            statusPass =
              row.results[toolIdx]?.values[columnIdx]?.raw === status ||
              statusPass ||
              emptyRowPass;
            columnPass = categoryPass && statusPass;
          } else {
            const rawValue = row.results[toolIdx]?.values[columnIdx]?.raw;
            if (isNil(rawValue)) {
              columnPass = false;
              continue;
            }
            const rawStr = String(rawValue);
            columnPass =
              columnPass ||
              String(value) === rawStr ||
              rawStr.includes(String(value));
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
