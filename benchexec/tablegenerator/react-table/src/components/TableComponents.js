// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import React from "react";
import { formatColumnTitle, getRunSetName } from "../utils/utils.js";

export const SelectColumnsButton = ({ handler, ...other }) => (
  <button onClick={handler} {...other}>
    Select Columns
  </button>
);

export const StandardColumnHeader = ({
  column,
  title = "Click here to sort. Hold shift to multi-sort",
  children,
  ...other
}) => (
  <div title={title} {...other}>
    {children || formatColumnTitle(column)}
  </div>
);

export const RunSetHeader = ({ runSet, ...other }) => (
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
}) => {
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

const createSeparatorColumn = (runSetIdx) =>
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

export const createRunSetColumns = (runSet, runSetIdx, createColumn) => [
  createSeparatorColumn(runSetIdx),
  {
    Header: <RunSetHeader runSet={runSet} />,
    columns: runSet.columns.map((column, columnIdx) =>
      createColumn(runSetIdx, column, columnIdx),
    ),
    id: "runset-column",
  },
];
