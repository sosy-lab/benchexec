/* SPDX-License-Identifier: Apache-2.0
 *
 * BenchExec is a framework for reliable benchmarking.
 * This file is part of BenchExec.
 * Copyright (C) Dirk Beyer. All rights reserved.
 */
import React from "react";

const prepareTableData = ({ head, tools, rows, stats, props }) => {
  return {
    tableHeader: head,
    tools: tools.map((tool) => ({
      ...tool,
      isVisible: true,
      columns: tool.columns.map((column) => ({ ...column, isVisible: true })),
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
    const numStart = Number(start);
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
  stringAsBoolean,
};
