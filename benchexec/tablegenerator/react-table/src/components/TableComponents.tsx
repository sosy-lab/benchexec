// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import React from "react";
import { formatColumnTitle, getRunSetName } from "../utils/utils";

/* ============================================================
 * Domain Types
 * ============================================================
 */

/**
 * Minimal shape of a column definition as required by formatColumnTitle(...).
 */
type ColumnTitleLike = {
  unit?: string;
  display_title: React.ReactNode;
};

/**
 * Minimal runset metadata as required by getRunSetName(...).
 */
type RunSetMetaLike = {
  tool: string;
  date: string;
  niceName: string;
};

/**
 * Minimal runset shape used in this module.
 */
type RunSetLike = RunSetMetaLike & {
  columns: ColumnTitleLike[];
};

/**
 * Minimal cell value used by StandardCell. This mirrors the data shape produced by the table generator.
 */
type CellValueLike = {
  href?: string;
  html?: string;
  raw?: React.ReactNode;
};

/**
 * Minimal cell shape used by StandardCell.
 * We keep it local-first and avoid importing react-table types here.
 */
type CellLike = {
  value: CellValueLike;
};

/**
 * Minimal react-table column shape used by createRunSetColumns/createSeparatorColumn.
 * Kept intentionally small and structural.
 */
type TableColumnLike = {
  Header?: React.ReactNode | string;
  accessor?: string;
  className?: string;
  columns?: TableColumnLike[];
  width?: number;
  minWidth?: number;
  id?: string;
};

/* ============================================================
 * Component Types
 * ============================================================
 */

type SelectColumnsButtonProps = React.HTMLAttributes<HTMLSpanElement> & {
  handler: React.MouseEventHandler<HTMLSpanElement>;
};

type StandardColumnHeaderProps = React.HTMLAttributes<HTMLDivElement> & {
  column: ColumnTitleLike;
  title?: string;
  children?: React.ReactNode;
};

type RunSetHeaderProps = React.HTMLAttributes<HTMLSpanElement> & {
  runSet: RunSetMetaLike;
};

type StandardCellProps = React.HTMLAttributes<HTMLElement> & {
  cell: CellLike;
  href?: string;
  toggleLinkOverlay: (
    ev: React.MouseEvent<HTMLAnchorElement>,
    href: string,
  ) => void;
  force?: boolean;
};

/* ============================================================
 * Components
 * ============================================================
 */

export const SelectColumnsButton = ({
  handler,
  ...other
}: SelectColumnsButtonProps): React.ReactElement => (
  <span onClick={handler} title="" className="selectColumns" {...other}>
    Click here to select columns
  </span>
);

export const StandardColumnHeader = ({
  column,
  title = "Click here to sort. Hold shift to multi-sort",
  children,
  ...other
}: StandardColumnHeaderProps): React.ReactElement => (
  <div title={title} {...other}>
    {children || formatColumnTitle(column)}
  </div>
);

export const RunSetHeader = ({
  runSet,
  ...other
}: RunSetHeaderProps): React.ReactElement => (
  <span className="header__tool-infos" {...other} title={getRunSetName(runSet)}>
    {getRunSetName(runSet)}
  </span>
);

export const StandardCell = ({
  cell,
  href = cell.value.href,
  toggleLinkOverlay,
  force = false,
  ...other
}: StandardCellProps): React.ReactElement | null => {
  const html = cell.value.html;
  const raw = html ? undefined : cell.value.raw;
  if (!force && !(raw || html)) {
    return null;
  }
  if (href) {
    return (
      <a
        href={href}
        onClick={(ev) => toggleLinkOverlay(ev, href)}
        dangerouslySetInnerHTML={html ? { __html: html } : undefined}
        {...other}
      >
        {raw}
      </a>
    );
  }
  return (
    <div
      dangerouslySetInnerHTML={html ? { __html: html } : undefined}
      {...other}
    >
      {raw}
    </div>
  );
};

/* ============================================================
 * Column Factory Helpers
 * ============================================================
 */

const createSeparatorColumn = (runSetIdx: number): Readonly<TableColumnLike> =>
  Object.freeze({
    Header: "",
    accessor: "separator" + runSetIdx,
    className: "separator",
    columns: [
      {
        accessor: "separator" + runSetIdx,
        className: "separator",
        width: 2,
        minWidth: 2,
      },
    ],
  });

export const createRunSetColumns = (
  runSet: RunSetLike,
  runSetIdx: number,
  createColumn: (
    runSetIndex: number,
    column: RunSetLike["columns"][number],
    columnIdx: number,
  ) => TableColumnLike,
): TableColumnLike[] => [
  createSeparatorColumn(runSetIdx),
  {
    Header: <RunSetHeader runSet={runSet} />,
    columns: runSet.columns.map((column, columnIdx) =>
      createColumn(runSetIdx, column, columnIdx),
    ),
    id: "runset-column",
  },
];
