// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import type React from "react";

/**
 * Naming convention: `*Like`
 *
 * Types suffixed with `Like` describe structural shapes of data
 * as they are received from JSON or prepared by `prepareTableData`.
 *
 * They are not strict domain entities but structural representations
 * that may contain optional or augmented fields.
 *
 * This helps distinguish:
 *
 *   - Tool → core stats model (used by computeStats)
 *   - ToolLike → prepared dataset model (used by Overview/ReactTable)
 *
 * The `Like` suffix indicates that the type is structurally compatible
 * but not necessarily identical to the canonical domain model.
 */

/* ============================================================================
 * Table column model
 * ========================================================================== */

type TableColumn = Readonly<{
  Header?: React.ReactNode;
  accessor?: string;
  id?: string;
  className?: string;
  columns?: ReadonlyArray<TableColumn>;
  width?: number;
  minWidth?: number;
}>;

export type { TableColumn };

/* ============================================================================
 * Table header (Benchmark Setup / Summary)
 * ========================================================================== */

type TableHeaderCell = readonly [unknown, number];

type TableHeaderItem = {
  content: TableHeaderCell[];
  id: string;
  name: string;
};

type TableHeaderLike = {
  task_id_names: string[];
  branch?: string | null;
  date?: TableHeaderItem;
  displayName?: TableHeaderItem;
  host?: TableHeaderItem;
  limit?: TableHeaderItem;
  options?: TableHeaderItem;
  os?: TableHeaderItem;
  property?: string | null;
  runset?: TableHeaderItem;
  system?: TableHeaderItem;
  title?: TableHeaderItem;
  tool?: TableHeaderItem;
  // other properties are passed through unchanged
  [key: string]: unknown;
};

/* ============================================================================
 * Tool / column shapes (prepared by prepareTableData)
 * ========================================================================== */

type ToolColumnLike = {
  title: string;
  display_title?: React.ReactNode;
  type?: string;
  unit?: string;
  max_width?: number;
  number_of_significant_digits?: number;
  relevant_for_diff?: boolean;
  hidden?: boolean;
  id?: string;

  // augmented fields
  colIdx?: number;

  // other properties are passed through unchanged
  [key: string]: unknown;
};

type ToolLike = {
  columns: ToolColumnLike[];
  benchmarkname?: string;
  name?: string;
  niceName?: string;
  tool?: string;
  version?: string;
  options?: string;
  timelimit?: string;
  memlimit?: string;
  cpuCores?: string;
  os?: string;
  cpu?: string;
  freq?: string;
  ram?: string;
  host?: string;
  date?: string;
  toolmodule?: string;
  project_url?: string;

  // augmented fields
  toolIdx?: number;
  scoreBased?: boolean;

  // other properties are passed through unchanged
  [key: string]: unknown;
};

export type { ToolColumnLike, ToolLike };

/* ============================================================================
 * Row / result shapes (prepared table rows)
 * ========================================================================== */

type ResultValue = {
  raw: string | number | null;
  html?: string;
};

type RowResultLike = {
  category: string;
  href: string;
  values: ResultValue[];
  score?: number | string | null;
  // other properties are passed through unchanged
  [key: string]: unknown;
};

type RowLike = {
  id: string[];
  href: string;
  results: RowResultLike[];
  // other properties are passed through unchanged
  [key: string]: unknown;
};

export type { RowLike };

/* ============================================================================
 * Stats blob as provided by dataset (pre-computeStats “shape”)
 * ========================================================================== */

type TableStats = {
  id: string;
  content: Array<Array<Record<string, number | string | null> | null>>;
  title?: string;
  description?: string;
};

/* ============================================================================
 * prepareTableData inputs/outputs
 * ========================================================================== */

type PrepareTableDataInput = {
  head: TableHeaderLike;
  tools: ToolLike[];
  rows: RowLike[];
  stats: TableStats[];
  props: unknown;
  initial: unknown;
};

type PreparedTableData = {
  tableHeader: TableHeaderLike;
  taskIdNames: string[];
  tools: Array<
    ToolLike & {
      toolIdx: number;
      columns: ToolColumnLike[];
      scoreBased: boolean;
    }
  >;
  columns: string[][];
  tableData: RowLike[];
  stats: TableStats[];
  properties: unknown;
  initial: unknown;
};

export type { PrepareTableDataInput, PreparedTableData };

/* ============================================================================
 * IDs used across table/filter code
 * ========================================================================== */

export type ColumnId = string;
export type RunsetId = string;

/* ============================================================================
 * Filter serialization types (used by URL helpers + Overview)
 * ========================================================================== */

/**
 * Serialized filter item used by URL serialization/deserialization helpers.
 * Named explicitly to avoid confusion with FilterBox filter definitions.
 */
type SerializedFilterItem = {
  id: string;
  value?: string;
  values?: string[];
  isTableTabFilter?: boolean;
};

/**
 * Decoded form of a filter ID.
 * `name` is the human-readable part encoded in the ID and may be missing for short IDs.
 */
type DecodedFilterId = {
  tool: string;
  name?: string;
  column?: string;
};

type StatusCategorySelection = {
  statusValues?: string[];
  categoryValues?: string[];
};

export type { SerializedFilterItem, DecodedFilterId, StatusCategorySelection };
