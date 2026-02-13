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
/* Status that will be used to identify whether empty rows should be shown. Currently,
   filtering for either categories or statuses creates filters for the other one as well.
   Since empty rows don't have a status, they will be filtered out all the time.
   To prevent this, this status placeholder will be used to indicate that empty rows
   should pass the status filtering. */
const statusForEmptyRows = "empty_row";

type ColumnType = "status" | "text" | string;

type ToolColumn = {
  type?: ColumnType;
} & Record<string, unknown>;

type Tool = {
  tool: string;
  date: string;
  niceName: string;
  columns: Array<ToolColumn | null | undefined>;
};

type ResultValueCell = {
  raw?: unknown;
} & Record<string, unknown>;

type ToolResult = {
  category: string;
  values: Record<string, ResultValueCell>;
};

type DataRow = {
  id: string[];
  results: ToolResult[];
};

type InputData = {
  tools: Tool[];
  rows: DataRow[];
};

type FilterableStatusColumn = ToolColumn & {
  kind: "status";
  type: "status";
  idx: number;
  categories: Record<string, true>;
  statuses: Record<string, true>;
};

type FilterableTextColumn = ToolColumn & {
  kind: "text";
  type: "text";
  idx: number;
  distincts: Record<string, true>;
};

type FilterableNumericColumn = ToolColumn & {
  kind: "numeric";
  idx: number;
  min: number;
  max: number;
};

type FilterableColumn =
  | FilterableStatusColumn
  | FilterableTextColumn
  | FilterableNumericColumn;

type FilterableTool = {
  name: string;
  columns: Array<
    | (Omit<FilterableStatusColumn, "categories" | "statuses"> & {
        categories: string[];
        statuses: string[];
      })
    | (Omit<FilterableTextColumn, "distincts"> & { distincts: string[] })
    | FilterableNumericColumn
    | undefined
  >;
};

/**
 * Prepares raw data for filtering by retrieving available distinct values as min
 * and max values of numeric fields
 *
 * @param {Object} data -  Data object received from json data
 */
const getFilterableData = ({ tools, rows }: InputData): FilterableTool[] => {
  const mapped = tools.map((tool, idx) => {
    let statusIdx: number | undefined;
    const { tool: toolName, date, niceName } = tool;
    const name = `${toolName} ${date} ${niceName}`;
    const columns: Array<FilterableColumn | undefined> = tool.columns.map(
      (col, colIdx) => {
        if (!col) {
          return undefined;
        }
        if (col.type === "status") {
          statusIdx = colIdx;
          return {
            ...col,
            kind: "status",
            type: "status",
            categories: {},
            statuses: {},
            idx: colIdx,
          };
        }
        if (col.type === "text") {
          return {
            ...col,
            kind: "text",
            type: "text",
            distincts: {},
            idx: colIdx,
          };
        }
        return {
          ...col,
          kind: "numeric",
          min: Infinity,
          max: -Infinity,
          idx: colIdx,
        };
      },
    );

    if (!isNil(statusIdx)) {
      const existing = columns[statusIdx];
      if (existing && existing.kind === "status") {
        existing.categories = {};
        existing.statuses = {};
      }
    }

    for (const row of rows) {
      const result = row.results[idx];
      // convention as of writing this commit is to postfix categories with a space character
      if (!isNil(statusIdx)) {
        const statusCol = columns[statusIdx];
        if (statusCol?.kind === "status") {
          statusCol.categories[`${result.category} `] = true;
        }
      }

      for (const colIdx in result.values) {
        const { raw } = result.values[colIdx];
        const filterCol = columns[Number(colIdx)];
        if (!filterCol || isNil(raw)) {
          continue;
        }

        if (filterCol.kind === "status") {
          filterCol.statuses[String(raw)] = true;
        } else if (filterCol.kind === "text") {
          filterCol.distincts[String(raw)] = true;
        } else {
          const num = Number(raw);
          filterCol.min = Math.min(filterCol.min, num);
          filterCol.max = Math.max(filterCol.max, num);
        }
      }
    }

    return {
      name,
      columns: columns.map((column) => {
        if (!column) {
          return undefined;
        }

        if (column.kind === "status") {
          const { categories, statuses, ...rest } = column;
          return {
            ...rest,
            categories: Object.keys(categories),
            statuses: Object.keys(statuses),
          };
        }

        if (column.kind === "text") {
          const { distincts, ...rest } = column;
          return { ...rest, distincts: Object.keys(distincts) };
        }

        return column;
      }),
    };
  });
  return mapped;
};

type SimpleRowForCellAccess = Record<string, unknown>;

type SimpleFilter = {
  id: string;
  value: string;
};

const applyNumericFilter = (
  filter: SimpleFilter,
  row: SimpleRowForCellAccess,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  cell: unknown,
): boolean | undefined => {
  const raw = getRawOrDefault(
    row[filter.id] as { raw?: unknown } | null | undefined,
    undefined,
  );
  if (raw === undefined) {
    // empty cells never match
    return undefined;
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
  filter: SimpleFilter,
  row: SimpleRowForCellAccess,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  cell: unknown,
): boolean | undefined => {
  const raw = getRawOrDefault(
    row[filter.id] as { raw?: unknown } | null | undefined,
    undefined,
  );
  if (raw === undefined) {
    // empty cells never match
    return undefined;
  }
  return String(raw).includes(filter.value);
};

type FilterInput = {
  id: string;
  value?: string;
  type?: string;
  values?: string[];
};

type MatcherDiffEntry = { col: number };
type MatcherIdEntry = { value?: string; values?: string[] };

type NumericClause = { min: number; max: number };
type CategoryClause = { category: string };
type StatusClause = { status: string };
type ValueClause = { value: string };
type MatcherClause =
  | NumericClause
  | CategoryClause
  | StatusClause
  | ValueClause;

type MatcherToolMap = Record<string, Record<string, MatcherClause[]>>;

type Matcher = MatcherToolMap & {
  diff?: MatcherDiffEntry[];
  id?: MatcherIdEntry;
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
const buildMatcher = (filters: FilterInput[]): Matcher => {
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
    const { tool, column } = decodeFilter(id);
    const toolIdx = Number(tool);
    const columnIdx = Number(column);

    if (Number.isNaN(toolIdx) || Number.isNaN(columnIdx)) {
      return acc;
    }

    if (value === "diff") {
      // this branch is noop as of now
      if (!acc.diff) {
        acc.diff = [];
      }
      acc.diff.push({ col: columnIdx });
      return acc;
    }
    const toolKey = String(tool);
    const colKey = String(columnIdx);

    if (!acc[toolKey]) {
      acc[toolKey] = {};
    }

    let filter: MatcherClause;
    if (
      typeof value === "string" &&
      isNumericColumn({ type }) &&
      value.includes(":")
    ) {
      const [minV, maxV] = value.split(":");
      const minNum = minV === "" ? -Infinity : Number(minV);
      const maxNum = maxV === "" ? Infinity : Number(maxV);
      filter = { min: minNum, max: maxNum };
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

    if (!acc[toolKey][colKey]) {
      acc[toolKey][colKey] = [];
    }
    acc[toolKey][colKey].push(filter);
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
const applyMatcher =
  (matcher: Matcher) =>
  (data: DataRow[]): DataRow[] => {
    let diffd = [...data];
    if (matcher.diff) {
      diffd = diffd.filter((row) => {
        for (const { col } of matcher.diff ?? []) {
          const vals: Record<string, true> = {};
          for (const tool of row.results) {
            const val = tool.values[String(col)]?.raw;
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
          id.some(
            (idName) => idName === idValue || regexToCompare.test(idName),
          ),
        );
      } else {
        // pre computing RegExp of each element of idValues array after excaping the special characters
        const idValuesWithRegex = (idValues ?? []).map((filterValue) => ({
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
    const out = diffd.filter((row) => {
      const rest = omit(["diff", "id"], matcher) as Omit<
        Matcher,
        "diff" | "id"
      >;

      for (const tool in rest) {
        const toolIdx = Number(tool);
        const toolMap = rest[tool];
        if (!toolMap || Number.isNaN(toolIdx)) {
          continue;
        }

        for (const column in toolMap) {
          const colIdx = Number(column);
          if (Number.isNaN(colIdx)) {
            continue;
          }

          let columnPass = false;
          let categoryPass = false;
          let statusPass = false;
          for (const filter of toolMap[column] ?? []) {
            const hasMinMax = "min" in filter && "max" in filter;
            const hasCategory = "category" in filter;
            const hasStatus = "status" in filter;
            const hasValue = "value" in filter;

            if (hasMinMax) {
              const { min, max } = filter as NumericClause;
              const rawValue =
                row.results[toolIdx]?.values[String(colIdx)]?.raw;
              if (isNil(rawValue)) {
                columnPass = false;
                continue;
              }
              const num = Number(rawValue);
              columnPass = columnPass || (num >= min && num <= max);
            } else if (hasCategory) {
              const { category } = filter as CategoryClause;
              categoryPass =
                row.results[toolIdx]?.category === category || categoryPass;
              columnPass = categoryPass && statusPass;
            } else if (hasStatus) {
              const { status } = filter as StatusClause;
              const emptyRowPass =
                row.results[toolIdx]?.category === "empty" &&
                status === statusForEmptyRows;
              statusPass =
                row.results[toolIdx]?.values[String(colIdx)]?.raw === status ||
                statusPass ||
                emptyRowPass;
              columnPass = categoryPass && statusPass;
            } else if (hasValue) {
              const { value } = filter as ValueClause;
              const rawValue =
                row.results[toolIdx]?.values[String(colIdx)]?.raw;
              if (isNil(rawValue)) {
                columnPass = false;
                continue;
              }
              const rawStr = String(rawValue);
              columnPass =
                columnPass || value === rawStr || rawStr.includes(value);
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
