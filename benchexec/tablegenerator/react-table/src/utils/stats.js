// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import { isNil, NumberFormatterBuilder } from "./utils";
import { enqueue } from "../workers/workerDirector";

const keysToIgnore = ["meta"];

const subStatSelector = {
  "total results": "total",
  "correct results": "correct-total",
  "correct true": "correct-true",
  "correct false": "correct-false",
  "incorrect results": "wrong-total",
  "incorrect true": "wrong-true",
  "incorrect false": "wrong-false",
};

/**
 * This method gets called on the initial render or whenever there is a
 * change to the underlying dataset.
 * This usually happens whenever the user sets a filter.
 *
 * It handles the dispatching of stat calculation jobs as well as
 * necessary transformation to bring the calculation results into the
 * required format.
 */
export const computeStats = async ({ tools, tableData, stats, asFiltered }) => {
  const formatter = buildFormatter(tools);
  let res = await processData({ tools, tableData, formatter });

  const availableStats = stats
    .map((row) => subStatSelector[row.title.replace(/&nbsp;/g, "")])
    .filter((element) => !isNil(element));
  const cleaned = cleanupStats(res, formatter, availableStats);

  // fill up stat array to match column mapping

  // The result of our stat calculation only contains relevant columns.
  // The stat table however requires a strict ordering of columns that also
  // includes columns that are not even rendered.
  //
  // In order to ensure a consistent layout we iterate through all columns
  // of the runset and append dummy objects until we reach a column that we
  // have calculated data for
  res = cleaned.map((tool, toolIdx) => {
    const out = [];
    const toolColumns = tools[toolIdx].columns;
    let pointer = 0;
    let curr = toolColumns[pointer];

    for (const col of tool) {
      const { title } = col;
      while (pointer < toolColumns.length && title !== curr.title) {
        // irrelevant column
        out.push({});
        pointer++;
        curr = toolColumns[pointer];
      }
      if (pointer >= toolColumns.length) {
        break;
      }
      // relevant column
      out.push(col);
      pointer++;
      curr = toolColumns[pointer];
    }

    return out;
  });

  if (asFiltered) {
    return addAsFilteredRow({
      newStats: res,
      stats,
    });
  } else {
    const transformed = stats.map((row) => {
      const title = row.title.replace(/&nbsp;/g, "");
      const content = row.content.map((tool, toolIdx) => {
        const key = subStatSelector[title];
        if (!key || !res[toolIdx]) {
          return tool;
        }
        return res[toolIdx].map((col) => col[key]);
      });
      return { ...row, content };
    });

    return transformed;
  }
};

/**
 * Creates a number formatters for each tool and column and
 * configures them with the columns defined number of significant digits
 *
 * @param {object[]} tools
 */
const buildFormatter = (tools) =>
  tools.map((tool, tIdx) =>
    tool.columns.map((column, cIdx) => {
      const { number_of_significant_digits: sigDigits } = column;
      return new NumberFormatterBuilder(sigDigits, `${tIdx}-${cIdx}`);
    }),
  );

const maybeRound =
  (key, maxDecimalInputLength, columnIdx) =>
  (number, { significantDigits }) => {
    const asNumber = Number(number);
    const [integer, decimal] = number.split(".");

    if (["sum", "avg", "stdev"].includes(key)) {
      // for cases when we have no significant digits defined,
      // we want to pad avg and stdev to two digits
      if (isNil(significantDigits) && key !== "sum") {
        return asNumber.toFixed(2);
      }
      // integer value without leading 0
      const cleanedInt = integer.replace(/^0+/, "");
      // decimal value without leading 0, if cleanedInt is empty (evaluates to zero)
      let cleanedDec = decimal || "";
      if (cleanedInt === "") {
        cleanedDec = cleanedDec.replace(/^0+/, "");
      }

      // differences in length between input value with maximal length and current value
      const deltaInputLength = maxDecimalInputLength - (decimal?.length ?? 0);

      // differences in length between num of significant digits and current value
      const deltaSigDigLength =
        significantDigits - (cleanedInt.length + cleanedDec.length);

      // if we have not yet filled the number of significant digits, we could decide to pad
      const paddingPossible = deltaSigDigLength > 0;

      const missingDigits = (decimal?.length ?? 0) + deltaSigDigLength;

      if (deltaInputLength > 0 && paddingPossible && key !== "stdev") {
        if (deltaInputLength > deltaSigDigLength) {
          // we want to pad to the smaller value (sigDigits vs maxDecimal)
          return asNumber.toFixed(missingDigits);
        }
        return asNumber.toFixed(maxDecimalInputLength);
      }

      // if avg was previously padded to fill the number of significant digits,
      // we want to make sure, that we don't go over the maximumDecimalDigits
      if (
        key === "avg" &&
        !paddingPossible &&
        deltaInputLength < 0 &&
        number[number.length - 1] === "0"
      ) {
        return asNumber.toFixed(maxDecimalInputLength);
      }

      if (key === "stdev" && paddingPossible) {
        return asNumber.toFixed(missingDigits);
      }
    }

    return number;
  };

/**
 * Used to apply formatting to calculated stats and to remove
 * values that are not displayable
 *stats
 * @param {object[][]} stats
 * @param {Function[][]} formatter
 */
const cleanupStats = (unfilteredStats, formatter, availableStats) => {
  const stats = unfilteredStats.map((tool, toolIdx) =>
    tool.map((col, colIdx) => {
      const { columnType } = col;
      const out = { columnType };

      for (const visibleStats of availableStats) {
        const currentCol = col[visibleStats];
        if (!currentCol) {
          continue;
        }
        out[visibleStats] = currentCol;
        if (currentCol?.sum ?? false) {
          formatter[toolIdx][colIdx].addDataItem(currentCol.sum);
        }
      }
      return out;
    }),
  );

  for (const to in formatter) {
    for (const co in formatter[to]) {
      // we build all formatters which makes them ready to use
      formatter[to][co] = formatter[to][co].build();
    }
  }

  const cleaned = stats.map((tool, toolIdx) =>
    tool
      .map(({ columnType, ...column }, columnIdx) => {
        const out = {};
        // if no total is calculated, then no values suitable for calculation were found
        if (column.total === undefined) {
          return undefined;
        }
        for (const [resultKey, result] of Object.entries(column)) {
          const rowRes = {};
          const meta = result?.meta;
          for (let [key, value] of Object.entries(result)) {
            // we ignore any of these defined keys
            if (keysToIgnore.includes(key)) {
              continue;
            }

            const maxDecimalInputLength = meta?.maxDecimals ?? 0;

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
                    additionalFormatting: maybeRound(
                      key,
                      maxDecimalInputLength,
                      columnIdx,
                    ),
                  });
                } else {
                  rowRes[key] = formatter[toolIdx][columnIdx](value, {
                    leadingZero: true,
                    whitespaceFormat: false,
                    html: false,
                    additionalFormatting: maybeRound(
                      key,
                      maxDecimalInputLength,
                      columnIdx,
                    ),
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

const addAsFilteredRow = ({ newStats, stats }) => {
  // our stats template to steal from

  const templ = [...stats];

  const filteredRow = newStats.map((tool) =>
    tool.map(({ total }) => ({ ...total })),
  );

  // Insert filtered row as first indented row.
  const i = templ.findIndex((row) => row.title.startsWith("&nbsp;"));
  templ.splice(i < 0 ? templ.length : i, 0, {
    description: "using the current set of filters configured in this table",
    title: "&nbsp;&nbsp;&nbsp;&nbsp;filtered tasks",
    content: filteredRow,
  });

  return templ;
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

const prepareRows = (
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
const splitColumnsWithMeta = (tools) => (preppedRows, toolIdx) => {
  const out = [];
  for (const { row, categoryType, resultType } of preppedRows) {
    for (const columnIdx in row) {
      const column = row[columnIdx].raw;
      const curr = out[columnIdx] || [];
      // we attach extra meta information for later use in calculation and mapping
      // of results
      const { type: columnType, title: columnTitle } =
        tools[toolIdx].columns[columnIdx];

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
const processData = async ({ tools, tableData, formatter }) => {
  const catAccessor = (toolIdx, row) => row.results[toolIdx].category;
  const statAccessor = (toolIdx, row) => row.results[toolIdx].values[0].raw;
  const promises = [];

  const splitRows = [];
  for (const toolIdx in tools) {
    splitRows.push(
      prepareRows(tableData, toolIdx, catAccessor, statAccessor, formatter),
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

  return res;
};
