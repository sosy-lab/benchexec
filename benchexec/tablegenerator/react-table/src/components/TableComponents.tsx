// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import React from "react";
import { formatColumnTitle, getRunSetName } from "../utils/utils";

/* ============================================================================
 * Table column model (minimal subset used here)
 * ========================================================================== */

export type TableColumn = Readonly<{
  Header?: React.ReactNode;
  accessor?: string;
  id?: string;
  className?: string;
  columns?: ReadonlyArray<TableColumn>;
  width?: number;
  minWidth?: number;
}>;

/* ============================================================================
 * Domain types
 * ========================================================================== */

type RunSet = {
  tool: string;
  date: string;
  niceName: string;
  columns: ReadonlyArray<{
    unit?: string;
    display_title: React.ReactNode;
  }>;
};

type CellValue = {
  href?: string;
  html?: string;
  raw?: React.ReactNode;
};

type TableCell = {
  value: CellValue;
};

/* ============================================================================
 * Component props
 * ========================================================================== */

type SelectColumnsButtonProps = {
  handler: React.MouseEventHandler<HTMLSpanElement>;
} & Omit<React.HTMLAttributes<HTMLSpanElement>, "onClick">;

type StandardColumnHeaderProps = {
  column: { unit?: string; display_title: React.ReactNode };
  title?: string;
  children?: React.ReactNode;
} & React.HTMLAttributes<HTMLDivElement>;

type RunSetHeaderProps = {
  runSet: { tool: string; date: string; niceName: string };
} & React.HTMLAttributes<HTMLSpanElement>;

type StandardCellProps = {
  cell: TableCell;
  href?: string;
  toggleLinkOverlay: (
    ev: React.MouseEvent<HTMLAnchorElement>,
    href: string,
  ) => void;
  force?: boolean;
} & React.HTMLAttributes<HTMLElement>;

/* ============================================================================
 * Components
 * ========================================================================== */

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

/* ============================================================================
 * Column factory helpers
 * ========================================================================== */

const createSeparatorColumn = (runSetIdx: number): TableColumn =>
  Object.freeze({
    Header: "",
    accessor: `separator${runSetIdx}`,
    className: "separator",
    columns: [
      {
        accessor: `separator${runSetIdx}`,
        className: "separator",
        width: 2,
        minWidth: 2,
      },
    ],
  });

type CreateColumnFn = (
  runSetIdx: number,
  column: RunSet["columns"][number],
  columnIdx: number,
) => TableColumn;

export const createRunSetColumns = (
  runSet: RunSet,
  runSetIdx: number,
  createColumn: CreateColumnFn,
): ReadonlyArray<TableColumn> => [
  createSeparatorColumn(runSetIdx),
  {
    Header: <RunSetHeader runSet={runSet} />,
    columns: runSet.columns.map((column, columnIdx) =>
      createColumn(runSetIdx, column, columnIdx),
    ),
    id: "runset-column",
  },
];
