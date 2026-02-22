// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

/* ============================================================================
 * Input data shapes used by filtering
 * ========================================================================== */

type RawCellLike = {
  raw?: string | number | null;
};

type FilterTableRowResult = {
  category: string;
  values: RawCellLike[];
};

type FilterTableRow = {
  id: string[];
  results: FilterTableRowResult[];
};

type FilterToolColumn = {
  type?: string;
  title: string;
  [key: string]: unknown;
};

type FilterTool = {
  tool: string;
  date: string;
  niceName: string;
  columns: Array<FilterToolColumn | undefined>;
};

type Dataset = {
  tools: FilterTool[];
  rows: FilterTableRow[];
};

export type { FilterTableRow, Dataset };

/* ============================================================================
 * Filter UI input (decoded/working representation)
 * ========================================================================== */

/**
 * Filter item as used by the filter engine and URL serializer/deserializer.
 * Includes `type` because Overview adds it dynamically based on column metadata.
 */
type FilterUIItem = {
  id: string;
  value?: string;
  type?: string;
  values?: string[];
};

export type { FilterUIItem };

/* ============================================================================
 * Matcher (compiled filters)
 * ========================================================================== */

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

export type { ColumnFilter, ToolMatcher, Matcher };

/* ============================================================================
 * Intermediate column shapes used while extracting distinct values
 * ========================================================================== */

type IntermediateStatusColumn = FilterToolColumn & {
  type: "status";
  categories: Record<string, true>;
  statuses: Record<string, true>;
  idx: number;
};

type IntermediateTextColumn = FilterToolColumn & {
  type: "text";
  distincts: Record<string, true>;
  idx: number;
};

type IntermediateNumericColumn = FilterToolColumn & {
  min: number;
  max: number;
  idx: number;
};

type IntermediateColumn =
  | IntermediateStatusColumn
  | IntermediateTextColumn
  | IntermediateNumericColumn;

export type {
  IntermediateStatusColumn,
  IntermediateTextColumn,
  IntermediateNumericColumn,
  IntermediateColumn,
};
