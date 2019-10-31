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

const isNil = data => data === undefined || data === null;

const sortMethod = (a, b) => {
  const aValue = a.original || -Infinity;
  const bValue = b.original || -Infinity;
  return bValue - aValue;
};

const pathOr = (defaultValue, path) => data => {
  if (!path || !(path instanceof Array) || !data) {
    return undefined;
  }
  let subPathResult = data;
  for (const node of path) {
    subPathResult = subPathResult[node];
    if (isNil(subPathResult)) {
      return defaultValue;
    }
  }
  return subPathResult;
};

const pipe = (...functions) => data => {
  let subResult = data;
  for (const func of functions) {
    subResult = func(subResult);
  }
  return subResult;
};

const maybeTransformToLowercase = data =>
  data && typeof data === "string" ? data.toLowerCase() : data;

const isOkStatus = status => {
  return status === 0 || status === 200;
};

export {
  prepareTableData,
  filterByRegex,
  sortMethod,
  isOkStatus,
  pathOr,
  isNil,
  pipe,
  maybeTransformToLowercase
};
