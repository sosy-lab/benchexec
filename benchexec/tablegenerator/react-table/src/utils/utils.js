/* SPDX-License-Identifier: Apache-2.0
 *
 * BenchExec is a framework for reliable benchmarking.
 * This file is part of BenchExec.
 * Copyright (C) Dirk Beyer. All rights reserved.
 */
const prepareTableData = ({ head, tools, rows, stats, props }) => {
  return {
    tableHeader: head,
    tools: tools.map(tool => ({
      ...tool,
      isVisible: true,
      columns: tool.columns.map(column => ({ ...column, isVisible: true }))
    })),
    columns: tools.map(tool => tool.columns.map(column => column.title)),
    table: rows,
    stats: stats,
    properties: props
  };
};

const filterByRegex = (filter, row, cell) => {
  const pattern = /((-?\d*\.?\d*):(-?\d*\.?\d*))|(-?\d*\.?\d*)/;

  const regex = filter.value.match(pattern);
  if (regex[2] === undefined) {
    return String(row[filter.id].formatted).startsWith(filter.value);
  } else if (!regex[3]) {
    if (+row[filter.id].original >= Number(regex[2])) {
      return row[filter.id];
    }
  } else if (!regex[2]) {
    if (+row[filter.id].original <= Number(regex[3])) {
      return row[filter.id];
    }
  } else if (
    row[filter.id].original >= Number(regex[2]) &&
    row[filter.id].original <= Number(regex[3])
  ) {
    return row[filter.id];
  }
  return false;
};

const sortMethod = (a, b) => {
  a = +a.original;
  b = +b.original;
  a = a === null || a === undefined ? -Infinity : a;
  b = b === null || b === undefined ? -Infinity : b;
  // a = typeof a === 'string' ? a.toLowerCase() : a
  // b = typeof b === 'string' ? b.toLowerCase() : b
  if (a > b) {
    return 1;
  }
  if (a < b) {
    return -1;
  }
  return 0;
};

const isOkStatus = status => {
  return status === 0 || status === 200;
};

export { prepareTableData, filterByRegex, sortMethod, isOkStatus };
