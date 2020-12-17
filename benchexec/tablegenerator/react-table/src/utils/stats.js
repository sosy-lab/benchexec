// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import { isNil, NumberFormatterBuilder } from "./utils";
import { enqueue } from "../workers/workerDirector";

/**
 * Creates a number formatters for each tool and column and
 * configures them with the columns defined number of significant digits
 *
 * @param {object[]} tools
 */
export const buildFormatter = (tools) =>
  tools.map((tool, tIdx) =>
    tool.columns.map((column, cIdx) => {
      const { number_of_significant_digits: sigDigits } = column;
      return new NumberFormatterBuilder(sigDigits, `${tIdx}-${cIdx}`);
    }),
  );

const maybeRound = (key) => (number, { significantDigits }) => {
  const asNumber = Number(number);
  if (["avg", "stdev"].includes(key)) {
    if (isNil(significantDigits)) {
      return asNumber.toFixed(2);
    }
    if (key === "stdev") {
      // special case "stdev", we want to pad stdev to match the number of significant digits
      const [integer, decimal] = number.split(".");
      let offset = 0;
      let includedNums = 0;
      let out = number;
      if (integer !== "0") {
        includedNums += integer.length;
      }
      if (decimal) {
        if (includedNums === 0) {
          const { 0: matched } = decimal.match(/^0*/, "");
          offset += matched.length;
        }
      }
      return Number(out).toFixed(offset + (significantDigits - includedNums));
    }
    return number;
  }
  //console.log({ key, number, significantDigits });

  return number;
};

/**
 * Used to apply formatting to calculated stats and to remove
 * values that are not displayable
 *
 * @param {object[][]} stats
 * @param {Function[][]} formatter
 */
export const cleanupStats = (stats, formatter) => {
  const cleaned = stats.map((tool, toolIdx) =>
    tool
      .map((column, columnIdx) => {
        const out = {};
        // if no total is calculated, then no values suitable for calculation were found
        if (column.total === undefined) {
          return undefined;
        }
        for (const [resultKey, result] of Object.entries(column)) {
          const rowRes = {};

          for (let [key, value] of Object.entries(result)) {
            // attach the title to the stat item
            // this will later be used to ensure correct ordering of columns
            if (key === "title") {
              out.title = value;
              continue;
            }
            // if we have numeric values or 'NaN' we want to apply formatting
            if (
              !isNil(value) &&
              (!isNaN(value) || value === "NaN") &&
              formatter[toolIdx][columnIdx]
            ) {
              try {
                if (key === "sum") {
                  rowRes[key] = formatter[toolIdx][columnIdx](value, {
                    leadingZero: false,
                    whitespaceFormat: true,
                    html: true,
                    additionalFormatting: maybeRound(key),
                  });
                } else {
                  rowRes[key] = formatter[toolIdx][columnIdx](value, {
                    leadingZero: true,
                    whitespaceFormat: false,
                    html: false,
                    additionalFormatting: maybeRound(key),
                  });
                }
              } catch (e) {
                console.error({
                  key,
                  value,
                  formatter: formatter[toolIdx][columnIdx],
                  e,
                });
              }
            }
          }

          out[resultKey] = rowRes;
        }

        return out;
      })
      .filter((i) => !isNil(i)),
  );
  return cleaned;
};

const RESULT_TRUE_PROP = "true";
//property holds
const RESULT_FALSE_PROP = "false";
//property does not hold

const RESULT_CLASS_TRUE = "true";
const RESULT_CLASS_FALSE = "false";
const RESULT_CLASS_OTHER = "other";

/**
 * @see result.py
 */
const classifyResult = (result) => {
  if (isNil(result)) {
    return RESULT_CLASS_OTHER;
  }
  if (result === RESULT_TRUE_PROP) {
    return RESULT_CLASS_TRUE;
  }
  if (result === RESULT_FALSE_PROP) {
    return RESULT_CLASS_FALSE;
  }
  if (result.startsWith(`${RESULT_FALSE_PROP}(`) && result.endsWith(")")) {
    return RESULT_CLASS_FALSE;
  }

  return RESULT_CLASS_OTHER;
};

export const prepareRows = (
  rows,
  toolIdx,
  categoryAccessor,
  statusAccessor,
  formatter,
) => {
  return rows.map((row) => {
    const cat = categoryAccessor(toolIdx, row);
    const stat = statusAccessor(toolIdx, row);

    const mappedCat = cat;
    const mappedRes = classifyResult(stat);

    return {
      categoryType: mappedCat,
      resultType: mappedRes,
      row: row.results[toolIdx].values,
    };
  });
};

/**
 * Transforms the dataset from a row-based layout into a column-based
 * layout for calculation of column stats.
 *
 * @param {object[]} tools
 */
export const splitColumnsWithMeta = (tools) => (preppedRows, toolIdx) => {
  const out = [];
  for (const { row, categoryType, resultType } of preppedRows) {
    for (const columnIdx in row) {
      const column = row[columnIdx].raw;
      const curr = out[columnIdx] || [];
      // we attach extra meta information for later use in calculation and mapping
      // of results
      const { type: columnType, title: columnTitle } = tools[toolIdx].columns[
        columnIdx
      ];

      curr.push({ categoryType, resultType, column, columnType, columnTitle });
      out[columnIdx] = curr;
    }
  }
  return out;
};

/**
 * Prepares the dataset for calculation, dispatches and collects calculations
 * and returns a cleaned set of calculated statistics.
 *
 * @param {object} options
 */
export const processData = async ({ tools, table, formatter }) => {
  const catAccessor = (toolIdx, row) => row.results[toolIdx].category;
  const statAccessor = (toolIdx, row) => row.results[toolIdx].values[0].raw;
  const start = Date.now();
  const promises = [];

  const splitRows = [];
  for (const toolIdx in tools) {
    splitRows.push(
      prepareRows(table, toolIdx, catAccessor, statAccessor, formatter),
    );
  }
  const columnSplitter = splitColumnsWithMeta(tools);

  const preparedData = splitRows.map(columnSplitter);
  // filter out non-relevant rows
  for (const toolIdx in preparedData) {
    preparedData[toolIdx] = preparedData[toolIdx].filter((i) => !isNil(i));
  }

  for (const toolDataIdx in preparedData) {
    const toolData = preparedData[toolDataIdx];
    const subPromises = [];
    for (const columnIdx in toolData) {
      const columns = toolData[columnIdx];
      subPromises.push(enqueue({ name: "stats", data: columns }));
    }
    promises[toolDataIdx] = subPromises;
  }

  const allPromises = promises.map((p) => Promise.all(p));
  const res = await Promise.all(allPromises);
  console.log(`Calculation took ${Date.now() - start}ms`);

  for (const tool in res) {
    for (const col in res[tool]) {
      for (const value of Object.values(res[tool][col])) {
        const sum = value?.sum ?? false;
        if (sum) {
          formatter[tool][col].addDataItem(sum);
        }
      }
    }
  }

  for (const to in formatter) {
    for (const co in formatter[to]) {
      // we build all formatters which makes them ready to use
      formatter[to][co] = formatter[to][co].build();
    }
  }

  const cleaned = cleanupStats(res, formatter);
  return cleaned;
};
