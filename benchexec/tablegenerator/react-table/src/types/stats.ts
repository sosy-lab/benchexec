// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import { statisticsRows } from "../utils/stats";

/* ============================================================
 * Types: Statistic Rows (UI metadata)
 * ============================================================ */

type StatisticRowDef = {
  title: string;
  indent?: number;
  description?: string;
};

type StatisticRowId = keyof typeof statisticsRows;

export type { StatisticRowDef, StatisticRowId };

/* ============================================================
 * Types: Dataset / Table Shapes
 * ============================================================ */

type RawCell = { raw: string };

type TableRowResult = {
  category: string;
  values: RawCell[];
};

type TableRow = {
  results: TableRowResult[];
};

type ToolColumn = {
  type?: string;
  title: string;
  number_of_significant_digits: number;
};

type Tool = {
  columns: ToolColumn[];
};

type StatRow = {
  id: StatisticRowId;
  content: unknown[][];
};

export type { RawCell, TableRow, Tool, StatRow };
