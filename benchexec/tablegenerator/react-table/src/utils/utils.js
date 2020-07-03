// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import React from "react";

const prepareTableData = ({ head, tools, rows, stats, props }) => {
  return {
    tableHeader: head,
    tools: tools.map((tool, idx) => ({
      ...tool,
      isVisible: true,
      toolIdx: idx,
      columns: tool.columns.map((column, idx) => ({
        ...column,
        colIdx: idx,
        isVisible: true,
      })),
    })),
    columns: tools.map((tool) => tool.columns.map((column) => column.title)),
    table: rows,
    stats: stats,
    properties: props,
  };
};

const isNumericColumn = (column) =>
  column.type === "count" || column.type === "measure";

const applyNumericFilter = (filter, row, cell) => {
  const raw = getRawOrDefault(row[filter.id]);
  if (raw === undefined) {
    // empty cells never match
    return;
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
    return raw.startsWith(filterParams[0]);
  }
  return false;
};

const applyTextFilter = (filter, row, cell) => {
  const raw = getRawOrDefault(row[filter.id]);
  if (raw === undefined) {
    // empty cells never match
    return;
  }
  return raw.includes(filter.value);
};

const isNil = (data) => data === undefined || data === null;

const getRawOrDefault = (value, def) =>
  isNil(value) || isNil(value.raw) ? def : value.raw;

const numericSortMethod = (a, b) => {
  const aValue = getRawOrDefault(a, +Infinity);
  const bValue = getRawOrDefault(b, +Infinity);
  return aValue - bValue;
};

const textSortMethod = (a, b) => {
  const aValue = getRawOrDefault(a, "").toLowerCase();
  const bValue = getRawOrDefault(b, "").toLowerCase();
  if (aValue === "") {
    return 1;
  }
  if (bValue === "") {
    return -1;
  }
  return aValue > bValue ? 1 : aValue < bValue ? -1 : 0;
};

const isOkStatus = (status) => {
  return status === 0 || status === 200;
};

// Best-effort attempt for calculating a meaningful column width
const determineColumnWidth = (column, min_width, max_width) => {
  let width = column.max_width; // number of chars in column
  if (min_width) {
    width = Math.max(width, min_width);
  }
  if (max_width) {
    width = Math.min(width, max_width);
  }
  if (!width) {
    width = 10;
  }

  return width * 8 + 20;
};

const formatColumnTitle = (column) =>
  column.unit ? (
    <>
      {column.display_title}
      <br />
      {`(${column.unit})`}
    </>
  ) : (
    column.display_title
  );

const getRunSetName = ({ tool, date, niceName }) => {
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
 *
 * @param {String} [str]
 */
const getHashSearch = (str) => {
  const urlParts = (str || document.location.href).split("?");
  const search = urlParts.length > 1 ? urlParts[1] : undefined;
  if (search === undefined || search.length === 0) {
    return {};
  }
  const keyValuePairs = search.split("&").map((i) => i.split("="));

  const out = {};
  for (const [key, value] of keyValuePairs) {
    out[key] = value;
  }
  return out;
};

/**
 *
 * @param {Object} params Object containing the params to be encoded as query params
 * @param {Boolean} [returnString] if true, only returns the url without setting it
 */
const setHashSearch = (
  params = {},
  options = { returnString: false, baseUrl: null },
) => {
  const optionTemplate = { returnString: false, baseUrl: null };
  const { returnString, baseUrl } = { ...optionTemplate, ...options };
  const url = (baseUrl || document.location.href).split("?")[0];
  const pairs = Object.keys(params).map((key) => `${key}=${params[key]}`);
  const searchString = `?${pairs.join("&")}`;
  const hrefString = `${url}${searchString}`;
  if (returnString) {
    return hrefString;
  }
  document.location.href = hrefString;
};

/**
 * Adds or update given key-value pairs to the query params
 *
 * @param {Object} param The Key-Value pair to be added to the current query param list
 */
const setParam = (param) => {
  setHashSearch({ ...getHashSearch(), ...param });
};

const stringAsBoolean = (str) => str === "true";

/**
 * Creates an object with an entry for each of the tools, identified by the index of the tool, that stores the hidden columns defined in the URL.
 * Each property contains an array of integers which represent the indexes of the columns of the corresponding runset that will be hidden.
 */
const createHiddenColsFromURL = (tools) => {
  const urlParams = getHashSearch();
  // Object containing all hidden runsets from the URL (= param "hidden")
  let hiddenTools = [];
  if (urlParams.hidden) {
    hiddenTools = urlParams.hidden
      .split(",")
      .filter((tool) => Number.isInteger(parseInt(tool)))
      .map((tool) => parseInt(tool));
  }

  // Object containing all hidden columns from the URL with an individual entry for each runset (= params of the form "hiddenX" for runset X)
  const hiddenCols = {};
  const hiddenParams = Object.keys(urlParams).filter((param) =>
    /hidden[0-9]+/.test(param),
  );
  hiddenParams.forEach((hiddenParam) => {
    const toolIdx = parseInt(hiddenParam.replace("hidden", ""));
    if (Number.isInteger(toolIdx)) {
      hiddenCols[toolIdx] = urlParams[hiddenParam]
        .split(",")
        .filter((col) => Number.isInteger(parseInt(col)))
        .map((col) => parseInt(col));
    }
  });

  // Set all columns of a hidden runset to hidden
  hiddenTools.forEach((hiddenToolIdx) => {
    hiddenCols[hiddenToolIdx] = tools
      .find((tool) => tool.toolIdx === hiddenToolIdx)
      .columns.map((column) => column.colIdx);
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
const getFirstVisibles = (tools, hiddenCols) => {
  let visibleCol;
  let visibleTool = tools.find((tool) => {
    visibleCol = tool.columns.find(
      (col) =>
        col.type !== "status" && !hiddenCols[tool.toolIdx].includes(col.colIdx),
    );
    return visibleCol;
  });

  if (!visibleCol) {
    visibleTool = tools.find(
      (tool) =>
        (visibleCol = tool.columns.find(
          (col) =>
            col.type === "status" &&
            !hiddenCols[tool.toolIdx].includes(col.colIdx),
        )),
    );
  }

  return visibleTool && visibleCol
    ? [visibleTool.toolIdx, visibleCol.colIdx]
    : [undefined, undefined];
};

export {
  prepareTableData,
  getRawOrDefault,
  isNumericColumn,
  applyNumericFilter,
  applyTextFilter,
  numericSortMethod,
  textSortMethod,
  determineColumnWidth,
  formatColumnTitle,
  getRunSetName,
  isOkStatus,
  isNil,
  EXTENDED_DISCRETE_COLOR_RANGE,
  getHashSearch,
  setHashSearch,
  setParam,
  createHiddenColsFromURL,
  stringAsBoolean,
  getFirstVisibles,
};
