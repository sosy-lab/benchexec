// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import React from "react";
import copy from "copy-to-clipboard";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faCopy } from "@fortawesome/free-regular-svg-icons";
import type {
  ToolColumnLike,
  ToolLike,
  RowLike,
  PrepareTableDataInput,
  PreparedTableData,
  ColumnId,
  RunsetId,
  SerializedFilterItem as FilterItem,
  DecodedFilterId,
  StatusCategorySelection,
} from "../types/reactTable";

/* ============================================================
 * Types: React Components
 * ============================================================ */

interface CopyableNodeProps {
  children?: React.ReactNode;
}

/* ============================================================
 * Types: URL / Hash / Query Parameters
 * ============================================================ */

type UrlLike = Pick<Location, "pathname"> | Pick<URL, "pathname">;

type URLParameters = Record<string, string>;

type SetURLParameterOptions = {
  callbacks: Array<() => void>;
  pushState: boolean;
};

type ConstructHashURLResult = {
  newUrl: string;
  queryString: string;
};

/* ============================================================
 * Types: Sorting / Cell Values
 * ============================================================ */

type RawValueLike = {
  raw?: unknown;
};

type SortCellValue = RawValueLike | null | undefined;

/* ============================================================
 * Types: Filter Serialization / Deserialization
 * ============================================================ */

type DistinctValuesByColumn = Record<ColumnId, string[]>;
type DistinctValuesByRunset = Record<RunsetId, DistinctValuesByColumn>;

type TokenizeResult = Record<string, string>;

type TokenHandlerResult =
  | { value: string }
  | { values: string[] }
  | { value: string; isTableTabFilter: true };

/* ============================================================
 * Types: Number Formatting
 * ============================================================ */

type NumberFormattingContext = {
  significantDigits: number;
  maxDecimalInputLength: number;
};

type NumberFormatterOptions = {
  whitespaceFormat: boolean;
  html: boolean;
  leadingZero: boolean;
  additionalFormatting: (x: string, ctx: NumberFormattingContext) => string;
};

/* A DOM node that allows its content to be copied to the clipboard. */
export class CopyableNode extends React.Component<CopyableNodeProps> {
  private readonly childRef: React.RefObject<HTMLSpanElement>;

  constructor(props: CopyableNodeProps) {
    super(props);
    this.childRef = React.createRef<HTMLSpanElement>();
  }

  render() {
    return (
      <>
        <span ref={this.childRef}>{this.props.children}</span>
        <button
          title="Copy to clipboard"
          style={{ margin: "1ex" }}
          onClick={() => {
            const node = this.childRef.current;
            if (node) {
              copy(node.innerText, { format: "text/plain" });
            }
          }}
        >
          <FontAwesomeIcon icon={faCopy} />
        </button>
      </>
    );
  }
}

/*
 * Split the path of a URL into a prefix (that is the longest prefix that is
 * shared with a second given URL) and the rest.
 * Both given URLs can be URL or Location instances.
 * Returns [prefix, rest] as an array of strings.
 * The "rest" always conains a least the file-part of the first URL
 * (after the last slash).
 * Protocol, query part and hash of the URL is dropped.
 */
export const splitUrlPathForMatchingPrefix = (
  url1: UrlLike,
  url2: UrlLike,
): [string, string] => {
  const path1 = url1.pathname.split("/");
  const path2 = url2.pathname.split("/");
  const firstDiffering = path1.findIndex(
    (element, index) => element !== path2[index],
  );
  return [
    path1.slice(0, firstDiffering).join("/"),
    path1.slice(firstDiffering).join("/"),
  ];
};

const emptyStateValue = "##########";

const prepareTableData = ({
  head,
  tools,
  rows,
  stats,
  props,
  initial,
}: PrepareTableDataInput): PreparedTableData => {
  return {
    tableHeader: head,
    taskIdNames: head.task_id_names,
    tools: tools.map((tool, idx) => ({
      ...tool,
      toolIdx: idx,
      columns: tool.columns.map((column, cIdx) => ({
        ...column,
        colIdx: cIdx,
      })),
      scoreBased: rows.every((row) => row.results[idx]?.score !== undefined),
    })),
    columns: tools.map((tool) =>
      tool.columns.map((column) => String(column.title)),
    ),
    tableData: rows,
    stats: stats,
    properties: props,
    initial: initial,
  };
};

const isNumericColumn = (column: { type?: string }): boolean =>
  column.type === "count" || column.type === "measure";

const isNil = (data: unknown): data is null | undefined =>
  data === undefined || data === null;

const getRawOrDefault = <T, D>(
  value: T | (T & RawValueLike) | null | undefined,
  def: D,
): unknown | D =>
  isNil(value) || isNil((value as RawValueLike).raw)
    ? def
    : (value as RawValueLike).raw;

const numericSortMethod = (a: SortCellValue, b: SortCellValue): number => {
  const aValue = getRawOrDefault(a, +Infinity);
  const bValue = getRawOrDefault(b, +Infinity);
  return Number(aValue) - Number(bValue);
};

const textSortMethod = (a: SortCellValue, b: SortCellValue): number => {
  const aValue = String(getRawOrDefault(a, "")).toLowerCase();
  const bValue = String(getRawOrDefault(b, "")).toLowerCase();
  if (aValue === "") {
    return 1;
  }
  if (bValue === "") {
    return -1;
  }
  return aValue > bValue ? 1 : aValue < bValue ? -1 : 0;
};

const isOkStatus = (status: unknown): boolean => {
  return status === 0 || status === 200;
};

const omit = <T extends Record<string, unknown>, K extends keyof T>(
  keys: readonly K[],
  data: T,
): Omit<T, K> => {
  const newKeys = (Object.keys(data) as Array<keyof T>).filter(
    (key) => !keys.includes(key as K),
  );
  const result = {} as Partial<T>;
  for (const key of newKeys) {
    result[key] = data[key];
  }
  return result as Omit<T, K>;
};

const without = <T,>(value: T, array: readonly T[]): T[] => {
  const out: T[] = [];
  for (const item of array) {
    if (item !== value) {
      out.push(item);
    }
  }
  return out;
};

// Best-effort attempt for calculating a meaningful column width
const determineColumnWidth = (
  column: { max_width?: number },
  min_width?: number,
  max_width?: number,
): number => {
  let width = column.max_width; // number of chars in column
  if (min_width) {
    width = Math.max(width ?? 0, min_width);
  }
  if (max_width) {
    width = Math.min(width ?? max_width, max_width);
  }
  if (!width) {
    width = 10;
  }

  return width * 8 + 20;
};

const path = (
  pathArr: Array<string | number>,
  data: unknown,
): unknown | undefined => {
  let last: unknown = data;
  for (const p of pathArr) {
    if (
      isNil(last) ||
      (typeof last !== "object" && typeof last !== "function")
    ) {
      return undefined;
    }
    const obj = last as Record<string, unknown>;
    last = obj[String(p)];
    if (isNil(last)) {
      return undefined;
    }
  }
  return last;
};

const pathOr = <T,>(
  pathArr: Array<string | number>,
  fallback: T,
  data: unknown,
): T => {
  const pathRes = path(pathArr, data);

  return pathRes === undefined ? fallback : (pathRes as T);
};

const formatColumnTitle = (column: {
  unit?: string;
  display_title: React.ReactNode;
}): React.ReactNode =>
  column.unit ? (
    <>
      {column.display_title}
      <br />
      {`(${column.unit})`}
    </>
  ) : (
    column.display_title
  );

const getRunSetName = ({
  tool,
  date,
  niceName,
}: {
  tool: string;
  date: string;
  niceName: string;
}): string => {
  return `${tool} ${date} ${niceName}`;
};

// Extended color list copied from
// https://github.com/uber/react-vis/blob/712ea622cf12f17bcc38bd6143fe6d22d530cbce/src/theme.js#L29-L51
// as advised in https://github.com/uber/react-vis/issues/872#issuecomment-404915958
const EXTENDED_DISCRETE_COLOR_RANGE = [
  "#19CDD7",
  "#DDB27C",
  "#88572C",
  "#FF991F",
  "#F15C17",
  "#223F9A",
  "#DA70BF",
  "#125C77",
  "#4DC19C",
  "#776E57",
  "#12939A",
  "#17B8BE",
  "#F6D18A",
  "#B7885E",
  "#FFCB99",
  "#F89570",
  "#829AE3",
  "#E79FD5",
  "#1E96BE",
  "#89DAC1",
  "#B3AD9E",
];

/**
 * Parses and decodes the search parameters except filter from the URL hash or a provided string.
 *
 * @param {string} - Optional string to parse. If not provided, parses the URL hash of the current document.
 * @returns {Object} - An object containing the parsed search parameters.
 */
const getURLParameters = (str?: string): URLParameters => {
  // Split the URL string into parts using "?" as a delimiter
  const urlParts = (str || window.location.href).split("?");

  // Extract the search part of the URL
  const search = urlParts.length > 1 ? urlParts.slice(1).join("?") : undefined;

  // If there are no search parameters, return an empty object
  if (search === undefined || search.length === 0) {
    return {};
  }

  // Split the search string into key-value pairs and generate an object from them
  const keyValuePairs = search.split("&").map((pair) => pair.split("="));
  const out: URLParameters = {};

  // All parameters in the search string are decoded except filter to allow filter handling later on its own
  for (const [key, ...value] of keyValuePairs) {
    out[decodeURI(key)] =
      key === "filter" ? value.join("=") : decodeURI(value.join("="));
  }

  return out;
};

/**
 * Constructs a query string from the provided parameters
 *
 * @param {Object} params - The parameters to be included in the query string. Any undefined or null values will be omitted.
 * @returns {string} - The constructed query string.
 */
export const constructQueryString = (
  params: Record<string, string | number | boolean | null | undefined>,
): string => {
  return Object.keys(params)
    .filter((key) => params[key] !== undefined && params[key] !== null)
    .map((key) => `${key}=${String(params[key])}`)
    .join("&");
};

/**
 * Constructs a URL hash from the provided parameters. It will merge the parameters with the existing ones in the URL hash after filtering out any undefined or null values.
 *
 * @param {string} url - The URL to be processed
 * @param {Object} params - The parameters to be included in the hash
 * @returns {string} - The constructed URL hash
 */
export const constructHashURL = (
  url: string,
  params: Record<string, string | number | boolean | null | undefined> = {},
): ConstructHashURLResult => {
  const existingParams = getURLParameters(url);
  const mergedParams: Record<
    string,
    string | number | boolean | null | undefined
  > = {
    ...existingParams,
    ...params,
  };

  const queryString = constructQueryString(mergedParams);
  const baseURL = url.split("?")[0];

  return {
    newUrl: queryString.length > 0 ? `${baseURL}?${queryString}` : baseURL,
    queryString: `?${queryString}`,
  };
};

/**
 * Sets or updates the search parameters in the URL hash of the current page. All the existing search parameters will not be disturbed.
 * It can also be used to remove a parameter from the URL by setting it's value to undefined.
 *
 * @param {Object} params - The parameters to be set or updated in the URL hash
 * @param {Object} options - The options object to configure the behavior of the function
 * @param {Array<Function>} options.callbacks - An array of callback functions to be executed after the URL hash is updated. Default is an empty array.
 * @param {boolean} options.pushState - A boolean value to determine whether to push the state to the history or not. Default is false.
 * @returns {void}
 */
const setURLParameter = (
  params: Record<string, string | number | boolean | null | undefined> = {},
  options: SetURLParameterOptions = { callbacks: [], pushState: false },
): void => {
  const { newUrl } = constructHashURL(window.location.href, params);

  if (options.pushState) {
    window.history.pushState({}, "", newUrl);
  }

  const callbacks = options.callbacks;
  if (callbacks && callbacks.length > 0) {
    for (const callback of callbacks) {
      callback();
    }
  }

  // In the browser we want to trigger a real navigation.
  // In the Jest/jsdom test environment, navigation (except hash changes)
  // is not implemented and produces noisy console.error logs.
  if (process.env.NODE_ENV !== "test") {
    window.location.href = newUrl;
  }
};

const makeUrlFilterDeserializer = (
  statusValues: DistinctValuesByRunset,
  categoryValues: DistinctValuesByRunset,
) => {
  const deserializer = makeFilterDeserializer({ categoryValues, statusValues });
  return (str: string): FilterItem[] | null => {
    const params = getURLParameters(str);
    if (params.filter) {
      return deserializer(params.filter);
    }
    return null;
  };
};

const makeSerializedFilterValue = (filter: {
  in?: string[];
  notIn?: string[];
}): string => {
  const parts: string[] = [];
  if (filter.in !== undefined) {
    parts.push(`in(${filter.in.map(escape).join(",")})`);
  }
  if (filter.notIn !== undefined) {
    parts.push(`notIn(${filter.notIn.map(escape).join(",")})`);
  }
  return parts.join(",");
};

const createDistinctValueFilters = (
  selected: string[],
  nominal: string[],
  trim = false,
): string => {
  const filter: { in?: string[]; notIn?: string[] } = {};
  // we want to minimize the needed space to encode the filter
  // if we have more than half of all values selected, we encode all not selected
  // values in "notIn", otherwise we encode all selected values in "in"
  if (selected.length > Math.floor(nominal.length / 2.0)) {
    const exclusions: string[] = [];
    for (const status of nominal) {
      if (!selected.includes(status)) {
        exclusions.push(trim ? status.trim() : status);
      }
    }
    filter.notIn = exclusions;
  } else {
    filter.in = selected.map((val) => (trim ? val.trim() : val));
  }
  return makeSerializedFilterValue(filter);
};

function makeStatusColumnFilter(
  filters: StatusCategorySelection,
  allStatusValues: DistinctValuesByRunset,
  tool: string,
  columnId: string,
  allCategoryValues: DistinctValuesByRunset,
): string {
  const statusColumnFilter: string[] = [];
  const { statusValues, categoryValues } = filters;
  const toolStatusValues = allStatusValues[tool]?.[columnId] ?? [];
  const toolCategoryValues = allCategoryValues[tool]?.[columnId] ?? [];

  const hasStatusFilter = !!statusValues;
  const hasCategoryFilter = !!categoryValues;

  if (hasStatusFilter) {
    const encodedFilter = createDistinctValueFilters(
      statusValues,
      toolStatusValues,
    );
    statusColumnFilter.push(`status(${encodedFilter})`);
    if (!hasCategoryFilter) {
      statusColumnFilter.push("category(empty())");
    }
  }
  if (hasCategoryFilter) {
    if (!hasStatusFilter) {
      statusColumnFilter.push("status(empty())");
    }
    const encodedFilter = createDistinctValueFilters(
      categoryValues,
      toolCategoryValues,
      true,
    );
    statusColumnFilter.push(`category(${encodedFilter})`);
  }
  return statusColumnFilter.join(",");
}

function escapeParentheses(value: unknown): string {
  if (typeof value !== "string") {
    throw new Error("Invalid value type");
  }
  return value.replace(/\(/g, "%28").replace(/\)/g, "%29");
}

export const makeRegExp = (value: unknown): RegExp => {
  if (typeof value !== "string") {
    throw new Error("Invalid value type for converting to RegExp");
  }
  const regexp = new RegExp(value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "ui");

  return regexp;
};

/**
 * Function to decode a filter ID string from the URL into its parts
 * @param {String} filterID - The filter ID to be decoded
 * @returns {Object} The decoded filter ID
 * @throws {Error} If the filter ID is invalid
 */
export const decodeFilter = (filterID: unknown): DecodedFilterId => {
  if (typeof filterID !== "string") {
    throw new Error("Invalid filter ID");
  }
  const splitedArray = filterID.split("_");

  if (splitedArray.length === 2) {
    throw new Error("Invalid filter ID");
  }

  // tool is always the first element value of the splitedArray
  // column is always the last element value of the splitedArray
  // name is the concatenation of remaining elements in between first and last element of splitedArray, separated by _
  return {
    tool: splitedArray[0],
    name:
      splitedArray.length > 2 ? splitedArray.slice(1, -1).join("_") : undefined,
    column: splitedArray.length > 2 ? splitedArray.at(-1) : undefined,
  };
};

const makeFilterSerializer =
  ({
    statusValues: allStatusValues,
    categoryValues: allCategoryValues,
  }: {
    statusValues: DistinctValuesByRunset;
    categoryValues: DistinctValuesByRunset;
  }) =>
  (filter: FilterItem[]): string => {
    interface GroupedColumn {
      name: string;
      categoryValues?: string[];
      statusValues?: string[];
      value?: string | string[];
    }
    const groupedRunsetFilters: Record<
      string,
      Record<string, GroupedColumn>
    > = {};
    let idsFilter: { values: string[] } | undefined = undefined;
    const tableTabIdFilters: Array<{ id: string; value: string }> = [];
    for (const { id, value, values, isTableTabFilter } of filter) {
      if (id === "id") {
        if (values && values.length > 0) {
          idsFilter = {
            values: values.map((val) => (val ? val : "")),
          };
        } else if (isTableTabFilter && typeof value === "string") {
          tableTabIdFilters.push({ id, value });
        }
        continue;
      }
      const { tool, name, column } = decodeFilter(id);
      const toolBucket = groupedRunsetFilters[tool] ?? {};
      const colKey = String(column);
      const columnBucket = toolBucket[colKey] ?? {
        name: escape(name ?? ""),
      };

      if (
        allStatusValues[tool]?.[colKey] ||
        allCategoryValues[tool]?.[colKey]
      ) {
        // we are processing a status column with checkboxes
        if (typeof value === "string" && value.endsWith(" ")) {
          // category value
          const selectedCategoryValues =
            (columnBucket.categoryValues as string[] | undefined) ?? [];
          selectedCategoryValues.push(value);
          columnBucket.categoryValues = selectedCategoryValues;
        } else if (typeof value === "string") {
          // status value
          const selectedStatusValues =
            (columnBucket.statusValues as string[] | undefined) ?? [];
          selectedStatusValues.push(value);
          columnBucket.statusValues = selectedStatusValues;
        }
      } else {
        columnBucket.value = value;
      }
      toolBucket[colKey] = columnBucket;
      groupedRunsetFilters[tool] = toolBucket;
    }

    // serialization part
    // we want to transform our filters into the following format:
    // [<idFilter>,]<runsetFilter>+
    // with
    // <idFilter> := id(values(<value>+))
    // <runsetFilter> := <runsetId>(<columnFilter>+)[,]
    // <columnFilter> := <columnId>*<name>*(<filter>)[,]
    // <filter> := <valueFilter>|<statusColumnFilter>
    // <valueFilter> := value(<value>)
    // <statusColumnFilter> := <statusFilter>|<categoryFilter>|<statusFilter>,<categoryFilter>
    // <statusFilter> := status(in(<value>+)|notIn(<value>+)|empty())
    // <categoryFilter> := category(in(<value>+)|notIn(<value>+)|empty())
    // <value> := <urlencodedTerminalValue>

    // one transformed example would be
    // 1(0*status*(statusFilter(notIn(true)),categoryFilter(in(correct,missing))),1*cputime*(value(%3A1120)))

    const runsetFilters: string[] = [];
    if (idsFilter) {
      const values = idsFilter.values;
      if (Array.isArray(values)) {
        runsetFilters.push(
          `id(values(${values
            .map((val) => escapeParentheses(encodeURIComponent(String(val))))
            .join(",")}))`,
        );
      }
    }
    if (tableTabIdFilters) {
      tableTabIdFilters.forEach((f) => {
        runsetFilters.push(
          `id_any(value(${escapeParentheses(encodeURIComponent(f.value))}))`,
        );
      });
    }
    for (const [tool, column] of Object.entries(groupedRunsetFilters)) {
      const columnFilters: string[] = [];
      for (const [columnId, filters] of Object.entries(column)) {
        const columnFilterHeader = `${columnId}*${String(filters.name)}*`;
        let filterPart = "";
        if (
          Array.isArray(filters.statusValues) ||
          Array.isArray(filters.categoryValues)
        ) {
          // <statusColumnFilter>
          const statusSelection: StatusCategorySelection = {
            statusValues: filters.statusValues,
            categoryValues: filters.categoryValues,
          };
          filterPart = makeStatusColumnFilter(
            statusSelection,
            allStatusValues,
            tool,
            columnId,
            allCategoryValues,
          );
        } else if (filters.value !== undefined) {
          // <valueFilter>
          filterPart = `value(${escape(String(filters.value))})`;
        }
        if (filterPart.length > 0) {
          columnFilters.push(`${columnFilterHeader}(${filterPart})`);
        }
      }
      if (columnFilters.length > 0) {
        runsetFilters.push(`${tool}(${columnFilters.join(",")})`);
      }
    }
    return runsetFilters.join(",");
  };

export const tokenizePart = (
  string: string,
  decodeValue = false,
): TokenizeResult => {
  const out: TokenizeResult = {};
  let openBrackets = 0;

  let buf = "";

  for (const char of string) {
    // we want to split the filter string on the highest level first
    if (char === "(") {
      buf += char;
      openBrackets++;
      continue;
    }
    if (char === ")") {
      buf += char;
      openBrackets--;
      if (openBrackets === 0) {
        const firstBracket = buf.indexOf("(");
        const key = buf.substr(0, firstBracket);
        const value = buf.substr(
          firstBracket + 1,
          buf.length - 1 - (firstBracket + 1),
        );
        out[key] = decodeValue ? decodeURIComponent(value) : value;
      }
      continue;
    }
    if (openBrackets === 0 && char === ",") {
      buf = "";
      continue;
    }
    buf += char;
  }
  return out;
};

const handleStatusColumnFilter = (
  token: "status" | "category",
  param: string,
  statusValues: DistinctValuesByColumn,
  categoryValues: DistinctValuesByColumn,
  column: string,
): Array<{ value: string }> => {
  // "in(a,b,c)"
  const parts = tokenizePart(param);
  const out: Array<{ value: string }> = [];
  for (const [method, stringItems] of Object.entries(parts)) {
    if (method === "in") {
      let items = stringItems.split(",").map(unescape);
      if (token === "category") {
        items = items.map((item) => `${item} `);
      }
      out.push(...items.map((item) => ({ value: item })));
    }
    if (method === "notIn") {
      let items = stringItems.split(",").map(unescape);
      const itemsToPush: Array<{ value: string }> = [];
      if (token === "category") {
        items = items.map((item) => `${item} `);

        for (const cat of categoryValues[column] ?? []) {
          if (!items.includes(cat)) {
            itemsToPush.push({ value: cat });
          }
        }
      } else {
        for (const stat of statusValues[column] ?? []) {
          if (!items.includes(stat)) {
            itemsToPush.push({ value: stat });
          }
        }
      }
      out.push(...itemsToPush);
    }
  }
  return out;
};

const tokenHandlers = (
  token: string,
  param: string,
  allStatusValues: DistinctValuesByColumn,
  allCategoryValues: DistinctValuesByColumn,
  column: string,
): TokenHandlerResult[] | undefined => {
  if (token === "values") {
    // wrapping return in array to allow vararg spreading
    return [{ values: param.split(",").map(unescape) }];
  }
  if (token === "value") {
    return [{ value: unescape(param) }];
  }
  if (token === "status" || token === "category") {
    return handleStatusColumnFilter(
      token,
      param,
      allStatusValues,
      allCategoryValues,
      column,
    );
  }
  return undefined;
};

const makeFilterDeserializer =
  ({
    categoryValues: allCategoryValues,
    statusValues: allStatusValues,
  }: {
    categoryValues: DistinctValuesByRunset;
    statusValues: DistinctValuesByRunset;
  }) =>
  (filterString: string): FilterItem[] => {
    const runsetFilters = tokenizePart(filterString);
    const out: FilterItem[] = [];
    for (const [token, filter] of Object.entries(runsetFilters)) {
      if (token === "id") {
        const tokenized = tokenizePart(filter);
        const handled = tokenHandlers(
          "values",
          tokenized["values"],
          {},
          {},
          "",
        );
        if (handled && "values" in handled[0]) {
          out.push({
            id: "id",
            ...handled[0],
          });
        }
        continue;
      } else if (token === "id_any") {
        out.push({
          id: "id",
          ...tokenizePart(filter, true),
          isTableTabFilter: true,
        });
        continue;
      }
      const runsetId = token;

      const columnFilters = tokenizePart(filter);
      const parsedColumnFilters: Record<string, FilterItem[]> = {};
      for (const [key, columnFilter] of Object.entries(columnFilters)) {
        const [columnId, columnTitle] = key.split("*");
        const name = `${runsetId}_${decodeURIComponent(
          columnTitle,
        )}_${columnId}`;
        const parsedFilters = parsedColumnFilters[name] || [];
        const tokenizedFilter = tokenizePart(columnFilter);

        for (const [filterToken, filterParam] of Object.entries(
          tokenizedFilter,
        )) {
          const handled = tokenHandlers(
            filterToken,
            filterParam,
            allStatusValues[runsetId] ?? {},
            allCategoryValues[runsetId] ?? {},
            columnId,
          );
          if (handled) {
            parsedFilters.push(...handled.map((h) => ({ id: name, ...h })));
          }
        }
        let hasStatus = false;
        let hasCategory = false;
        for (const t of Object.keys(tokenizedFilter)) {
          if (t === "status") {
            hasStatus = true;
          } else if (t === "category") {
            hasCategory = true;
          }
        }
        if ((hasStatus && !hasCategory) || (!hasStatus && hasCategory)) {
          // if we only have category or a status filter, it means that no
          // filter has been set for the other. We need to fill up the values
          if (!hasStatus) {
            for (const status of allStatusValues[runsetId]?.[columnId] ?? []) {
              parsedFilters.push({ id: name, value: status });
            }
          } else {
            for (const category of allCategoryValues[runsetId]?.[columnId] ??
              []) {
              parsedFilters.push({ id: name, value: category });
            }
          }
        }
        parsedColumnFilters[name] = parsedFilters;
        for (const parsedFilter of parsedFilters) {
          out.push(parsedFilter);
        }
      }
    }
    return out;
  };

const makeUrlFilterSerializer = (
  statusValues: DistinctValuesByRunset,
  categoryValues: DistinctValuesByRunset,
) => {
  const serializer = makeFilterSerializer({ statusValues, categoryValues });
  return (
    filter: FilterItem[] | null | undefined,
    options: SetURLParameterOptions,
  ): void => {
    if (!filter) {
      return setURLParameter({ filter: undefined }, options);
    }

    const encoded = serializer(filter);
    if (encoded) {
      return setURLParameter({ filter: encoded }, options);
    }

    return setURLParameter({ filter: undefined }, options);
  };
};

// Sets the URL parameters to the given string. Assumes that there is currently no hash or URL parameters defined.
const setConstantHashSearch = (paramString: string): void => {
  document.location.href = encodeURI(
    `${document.location.href}#${paramString}`,
  );
};

const stringAsBoolean = (str: string): boolean => str === "true";

const deepEquals = (
  a: Record<string, unknown>,
  b: Record<string, unknown>,
): boolean => {
  for (const key in a) {
    if (typeof a[key] === "function" && typeof b[key] === "function") {
      continue;
    }
    if (typeof a[key] !== typeof b[key]) {
      return false;
    } else if (Array.isArray(a[key]) || typeof a[key] === "object") {
      if (
        !deepEquals(
          a[key] as Record<string, unknown>,
          b[key] as Record<string, unknown>,
        )
      ) {
        return false;
      }
    } else {
      if (a[key] !== b[key]) {
        console.log(`${String(a[key])} !== ${String(b[key])}`);
        return false;
      }
    }
  }
  return true;
};

/**
 * Function to extract the names of the task id parts and to provide a mapping for filtering.
 * The returned array is of following form:
 * [
 *  {
 *    label: "example",
 *  }, {...}
 * ]
 *
 * where the label will be displayed over the input field of the task id filter and
 * the example value will be the input hint to further clarify the functionality.
 *
 * @param {*} rows - the rows array of the dataset
 */
const getTaskIdParts = (
  rows: RowLike[],
  taskIdNames: string[],
): Record<string, string> => {
  const ids = pathOr<string[]>(["0", "id"], [], rows);
  return ids.reduce(
    (acc: Record<string, string>, curr: string, idx: number) => ({
      ...acc,
      [taskIdNames[idx]]: curr,
    }),
    {},
  );
};

/**
 * Function to safely add two numbers in a way that should mitigate errors
 * caused by inaccurate floating point operations in javascript
 * @param {Number|String} a - The base number
 * @param {Number|String} b - The number to add
 *
 * @returns {Number} The result of the addition
 */
// WHEN EDITING THIS FUNCTION, ALSO EDIT THE COPY OF THIS FUNCTION IN src/woerks/scrips/stats.worker.js
const safeAdd = (a: number | string, b: number | string): number => {
  const aNum: number = typeof a === "string" ? Number(a) : a;
  const bNum: number = typeof b === "string" ? Number(b) : b;

  if (Number.isInteger(aNum) || Number.isInteger(bNum)) {
    return aNum + bNum;
  }

  const aString = a.toString();
  const aLength = aString.length;
  const aDecimalPoint = aString.indexOf(".");
  const bString = b.toString();
  const bLength = bString.length;
  const bDecimalPoint = bString.indexOf(".");

  const length = Math.max(aLength - aDecimalPoint, bLength - bDecimalPoint) - 1;

  return Number((aNum + bNum).toFixed(length));
};

const punctuationSpaceHtml = "&#x2008;";
const characterSpaceHtml = "&#x2007;";

/**
 * Builds and configures a formatting function that can format a number based on
 * the significant digits of the dataset for its column.
 * If whitespaceFormat in the returned function is set to true, the number will be
 * whitespace formatted as described on Page 24 in
 * https://www.sosy-lab.org/research/pub/2019-STTT.Reliable_Benchmarking_Requirements_and_Solutions.pdf
 *
 * @param {Number} significantDigits - Number of significant digits for this column
 */
class NumberFormatterBuilder {
  significantDigits: number;
  maxPositiveDecimalPosition: number;
  maxNegativeDecimalPosition: number;
  name: string;

  constructor(significantDigits: number, name = "Unknown") {
    this.significantDigits = significantDigits;
    this.maxPositiveDecimalPosition = -1;
    this.maxNegativeDecimalPosition = -1;
    this.name = name;
  }

  _defaultOptions: NumberFormatterOptions = {
    whitespaceFormat: false,
    html: false,
    leadingZero: true,
    additionalFormatting: (x) => x,
  };

  addDataItem(item: number): void {
    const formatted = this.format(item);
    const [positive, negative] = formatted.split(/\.|,/);
    this.maxPositiveDecimalPosition = Math.max(
      this.maxPositiveDecimalPosition,
      positive && positive !== "0" ? positive.length : 0,
    );
    this.maxNegativeDecimalPosition = Math.max(
      this.maxNegativeDecimalPosition,
      negative ? negative.length : 0,
    );
  }

  format(number: number): string {
    let stringNumber = number.toString();
    let prefix = "";
    let postfix = "";
    let pointer = 0;
    let addedNums = 0;
    let firstNonZero = false;
    let decimal = false;

    if (stringNumber === "NaN") {
      return "NaN";
    }
    if (stringNumber.endsWith("Infinity")) {
      return stringNumber.replace("Infinity", "Inf");
    }

    // handling exponential formatting of large (or small) numbers in javascript
    if (stringNumber.includes("e")) {
      const [coefficient, exponent] = stringNumber.split("-");
      let addedFactor = 0;
      if (coefficient.includes(".")) {
        addedFactor = 1;
      }
      stringNumber = Number(number).toFixed(Number(exponent) + addedFactor);
    }

    const decimalPos = stringNumber.replace(/,/, ".").indexOf(".");
    while (
      addedNums < this.significantDigits - 1 &&
      stringNumber.length > pointer
    ) {
      const current = stringNumber[pointer];
      if (current === "." || current === ",") {
        prefix += ".";
        decimal = true;
      } else {
        if (!firstNonZero) {
          if (current === "0") {
            pointer += 1;
            if (decimal) {
              prefix += current;
            }
            continue;
          }
          firstNonZero = true;
        }
        prefix += current;
        addedNums += 1;
      }
      pointer += 1;
    }
    postfix = stringNumber.substring(pointer);
    if (prefix === "" && postfix === "") {
      prefix = stringNumber;
    }
    if (prefix[0] === ".") {
      prefix = `0${prefix}`;
    }

    if (postfix !== "") {
      // hacky trickery
      // we force the postfix to turn into a decimal value with one leading integer
      // e.g. 5432 -> 5.432
      // this way we can round up to the first digit of the string
      const attachDecimal = postfix[0] === ".";
      postfix = postfix.replace(/\./, "");
      postfix = `${postfix[0]}.${postfix.substr(1)}`;
      const rounded = Math.round(Number(postfix));
      postfix = isNaN(rounded) ? "" : rounded.toString();
      //handle carry
      if (postfix.length > 1 && postfix[0] !== ".") {
        const overflow = postfix[0];
        postfix = postfix[1];
        const oldLength = prefix.length;
        const [, decPart] = prefix.split(".");
        const decimalLength = (decPart && decPart.length - 1) || 0;
        let toAdd = decPart ? "0." : "";
        let i = decimalLength;
        while (i > 0) {
          toAdd += "0";
          i -= 1;
        }

        toAdd += overflow;
        prefix = safeAdd(prefix, toAdd)
          .toFixed(decimalLength + 1)
          .substr(0, oldLength);
        while (prefix.length < oldLength) {
          prefix += "0";
        }
      }
      // fill up integer number;
      let end = decimalPos;
      if (attachDecimal) {
        postfix = `.${postfix}`;
      }

      if (decimalPos === -1) {
        end = stringNumber.length;
      }
      while (prefix.length + postfix.length < end) {
        postfix += "0";
      }
    }
    return `${prefix}${postfix}`;
  }

  build(): (
    number: number,
    options?: Partial<NumberFormatterOptions>,
  ) => string {
    return (number, options = {}) => {
      const { whitespaceFormat, html, leadingZero, additionalFormatting } = {
        ...this._defaultOptions,
        ...options,
      };

      const ctx: NumberFormattingContext = {
        significantDigits: this.significantDigits,
        maxDecimalInputLength: this.maxNegativeDecimalPosition,
      };
      if (isNil(this.significantDigits)) {
        return additionalFormatting(number.toString(), ctx);
      }
      let out = this.format(number);

      out = additionalFormatting(out, ctx);

      if (out === "NaN") {
        // we don't want to pad NaN
        return out;
      }

      if (whitespaceFormat) {
        const decSpace = html ? punctuationSpaceHtml : " ";
        let [integer, decimal] = out.split(/\.|,/);
        if (integer === "0" && !leadingZero) {
          integer = decimal ? "" : "0";
        }
        integer = integer || "";
        decimal = decimal || "";
        const decimalPoint = decimal ? "." : decSpace;
        /*         while (integer.length < this.maxPositiveDecimalPosition) {
          integer = ` ${integer}`;
        } */
        while (decimal.length < this.maxNegativeDecimalPosition) {
          decimal += " ";
        }
        if (html) {
          integer = integer.replace(/ /g, characterSpaceHtml);
          decimal = decimal.replace(/ /g, characterSpaceHtml);
        }

        return `${integer}${decimal ? decimalPoint : ""}${decimal}`;
      }
      if (!leadingZero && out.startsWith("0.")) {
        return out.substr(1);
      }
      return out;
    };
  }
}
/**
 * Creates an object with an entry for each of the tools, identified by the index of the tool, that stores the hidden columns defined in the URL.
 * Each property contains an array of integers which represent the indexes of the columns of the corresponding runset that will be hidden.
 */
const createHiddenColsFromURL = (
  tools: Array<
    ToolLike & {
      toolIdx: number;
      columns: Array<ToolColumnLike & { colIdx: number }>;
    }
  >,
): Record<number, number[]> => {
  const urlParams = getURLParameters();
  // Object containing all hidden runsets from the URL (= param "hidden")
  let hiddenTools: number[] = [];
  if (urlParams.hidden) {
    hiddenTools = urlParams.hidden
      .split(",")
      .filter(
        (hiddenTool) =>
          Number.isInteger(parseInt(hiddenTool)) &&
          tools.some((tool) => tool.toolIdx === parseInt(hiddenTool)),
      )
      .map((hiddenTool) => parseInt(hiddenTool));
  }

  // Object containing all hidden columns from the URL with an individual entry for each runset (= params of the form "hiddenX" for runset X)
  const hiddenCols: Record<number, number[]> = {};
  const hiddenParams = Object.keys(urlParams).filter((param) =>
    /hidden[0-9]+/.test(param),
  );
  hiddenParams.forEach((hiddenParam) => {
    const toolIdx = parseInt(hiddenParam.replace("hidden", ""));
    const tool = tools.find((t) => t.toolIdx === toolIdx);
    if (Number.isInteger(toolIdx) && tool) {
      hiddenCols[toolIdx] = urlParams[hiddenParam]
        .split(",")
        .filter(
          (hiddenCol) =>
            Number.isInteger(parseInt(hiddenCol)) &&
            tool.columns.some((col) => col.colIdx === parseInt(hiddenCol)),
        )
        .map((col) => parseInt(col));
    }
  });

  // Set all columns of a hidden runset to hidden
  hiddenTools.forEach((hiddenToolIdx) => {
    const tool = tools.find((t) => t.toolIdx === hiddenToolIdx);
    if (tool) {
      hiddenCols[hiddenToolIdx] = tool.columns.map(
        (column) => column.colIdx as number,
      );
    }
  });

  // Leave hidden columns for not mentioned tools empty
  tools.forEach((tool) => {
    if (!hiddenCols[tool.toolIdx]) {
      hiddenCols[tool.toolIdx] = [];
    }
  });

  return hiddenCols;
};

/**
 * Returns the index of the first runset that has a column that is not hidden and not of the type status, as well as the index
 * of the corresponding column. In case there is no such column, returns the index of the first runset that has a status column
 * that is not hidden, as well as the index of this column. In case there is also no such column, i.e. all columns of all runsets
 * are hidden, returns undefined for those values.
 **/
const getFirstVisibles = (
  tools: Array<
    ToolLike & {
      toolIdx: number;
      columns: Array<ToolColumnLike & { colIdx: number }>;
    }
  >,
  hiddenCols: Record<number, number[]>,
): [number | undefined, number | undefined] => {
  let visibleCol: (ToolColumnLike & { colIdx: number }) | undefined;
  let visibleTool = tools.find((tool) => {
    visibleCol = tool.columns.find(
      (col) =>
        col.type !== "status" &&
        !hiddenCols[tool.toolIdx].includes(col.colIdx as number),
    ) as (ToolColumnLike & { colIdx: number }) | undefined;
    return visibleCol;
  });

  if (!visibleCol) {
    visibleTool = tools.find((tool) => {
      visibleCol = tool.columns.find(
        (col) =>
          col.type === "status" &&
          !hiddenCols[tool.toolIdx].includes(col.colIdx as number),
      ) as (ToolColumnLike & { colIdx: number }) | undefined;
      return visibleCol;
    });
  }

  return visibleTool && visibleCol
    ? [visibleTool.toolIdx, visibleCol.colIdx]
    : [undefined, undefined];
};

/**
 * Checks if all distinct elements of the data param also
 * exist in the compare param.
 * Only to be used with primitives. Objects will be compared by reference.
 *
 *
 * @param {ReadonlyArray<string>} compare The array to compare elements to
 * @param {ReadonlyArray<string>} data The array to check
 */
const hasSameEntries = (
  compare: ReadonlyArray<string>,
  data: ReadonlyArray<string>,
): boolean => {
  const compareObj: Record<string, true> = {};

  for (const elem of compare) {
    compareObj[String(elem)] = true;
  }
  for (const elem of data) {
    if (isNil(compareObj[String(elem)])) {
      return false;
    }
  }

  return true;
};

/**
 * Naive check if a filter value is a category (currently identifiable by a trailing " ")
 * @param {string} item - the filter value
 * @returns {boolean} True if value is a category, else false
 */
const isCategory = (item: string): boolean =>
  !!(item && item[item.length - 1] === " ");

/**
 * This function uses string operations to get the smallest decimal part of a number.
 * If a number is an integer, the return value will be 1
 * A return type of string is used to prevent a small number to take the shape of
 * a scientific notation, as they are incompatible with the "step" attribute of
 * html inputs.
 *
 * @param {string} num - The number to check
 * @returns {string} - The smallest step
 */
const getStep = (num: string | number): string | number => {
  const stringRep = num.toString();
  const [, decimal] = stringRep.split(/,|\./);
  if (isNil(decimal) || decimal.length === 0) {
    return 1;
  }
  let out = ".";
  for (let i = 0; i < decimal.length - 1; i += 1) {
    out += "0";
  }
  out += "1";
  return out;
};

const identity = <T,>(x: T): T => x;
/**
 * Computes and returns all ids of the given columns that are hidden. Assumes that
 * the columns object is in the format that is used in the ReactTable and Summary component.
 */
const getHiddenColIds = (
  columns: Array<{ columns: Array<{ hidden?: boolean; id?: string }> }>,
): string[] => {
  const hiddenColIds: Array<string | undefined>[] = [];
  // Idx 0 is the title column and every uneven idx is the separator column, so only check for hidden cols in every even column entry greater than 0
  columns = columns.filter((col, idx) => idx % 2 === 0 && idx !== 0);
  columns.forEach((col) =>
    hiddenColIds.push(
      col.columns.filter((column) => column.hidden).map((column) => column.id),
    ),
  );
  return hiddenColIds
    .flat()
    .filter((id): id is string => typeof id === "string");
};

export {
  prepareTableData,
  getRawOrDefault,
  isNumericColumn,
  numericSortMethod,
  textSortMethod,
  determineColumnWidth,
  formatColumnTitle,
  getRunSetName,
  isOkStatus,
  isNil,
  EXTENDED_DISCRETE_COLOR_RANGE,
  getURLParameters,
  setConstantHashSearch,
  setURLParameter,
  createHiddenColsFromURL,
  stringAsBoolean,
  without,
  pathOr,
  path,
  omit,
  deepEquals,
  NumberFormatterBuilder,
  emptyStateValue,
  getTaskIdParts,
  getFirstVisibles,
  hasSameEntries,
  isCategory,
  getStep,
  identity,
  makeUrlFilterDeserializer,
  makeUrlFilterSerializer,
  makeFilterSerializer,
  makeFilterDeserializer,
  safeAdd,
  getHiddenColIds,
};
