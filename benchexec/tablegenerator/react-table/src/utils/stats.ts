// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import { isNil, NumberFormatterBuilder } from "./utils";
import { enqueue } from "../workers/workerDirector";

const keysToIgnore = new Set(["meta"] as const);

/* ============================================================
 * Types: Statistic Rows (UI metadata)
 * ============================================================ */

type StatisticRowDef = {
  title: string;
  indent?: number;
  description?: string;
};

export const statisticsRows = {
  total: { title: "all results" },
  correct: {
    indent: 1,
    title: "correct results",
    description:
      "(property holds + result is true) OR (property does not hold + result is false)",
  },
  correct_true: {
    indent: 2,
    title: "correct true",
    description: "property holds + result is true",
  },
  correct_false: {
    indent: 2,
    title: "correct false",
    description: "property does not hold + result is false",
  },
  correct_unconfirmed: {
    indent: 1,
    title: "correct-unconfirmed results",
    description:
      "(property holds + result is true) OR (property does not hold + result is false), but unconfirmed",
  },
  correct_unconfirmed_true: {
    indent: 2,
    title: "correct-unconfirmed true",
    description: "property holds + result is true, but unconfirmed",
  },
  correct_unconfirmed_false: {
    indent: 2,
    title: "correct-unconfirmed false",
    description: "property does not hold + result is false, but unconfirmed",
  },
  wrong: {
    indent: 1,
    title: "incorrect results",
    description:
      "(property holds + result is false) OR (property does not hold + result is true)",
  },
  wrong_true: {
    indent: 2,
    title: "incorrect true",
    description: "property does not hold + result is true",
  },
  wrong_false: {
    indent: 2,
    title: "incorrect false",
    description: "property holds + result is false",
  },
} as const;

const _statisticsRowsTypeCheck: Record<string, StatisticRowDef> =
  statisticsRows;
void _statisticsRowsTypeCheck;

type StatisticRowId = keyof typeof statisticsRows;

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

/* ============================================================
 * Types: Formatting
 * ============================================================ */

// This is intentionally minimal and matches only what this file needs.
type NumberFormatterBuilderLike = {
  addDataItem: (value: unknown) => void;
  build: () => FormatterFn;
};

type FormatterOptions = {
  leadingZero: boolean;
  whitespaceFormat: boolean;
  html: boolean;
  additionalFormatting: (
    value: string,
    opts: { significantDigits?: number },
  ) => string;
};

type FormatterFn = (value: unknown, options: FormatterOptions) => string;

type FormatterCell = NumberFormatterBuilderLike | FormatterFn;
type FormatterMatrix = FormatterCell[][];

/* ============================================================
 * Types: Worker result / intermediate shapes
 * ============================================================ */

type ComputedStatEntry = Record<string, unknown> & {
  meta?: { maxDecimals?: number };
  sum?: unknown;
};

type UnfilteredColumnStats = Record<string, unknown> & {
  columnType?: unknown;
};

type PreppedRow = {
  categoryType: string;
  resultType: string;
  row: RawCell[];
};

type SplitColumnItem = {
  categoryType: string;
  resultType: string;
  column: string;
  columnType?: string;
  columnTitle: string;
};

const asRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null;

/**
 * Remove all statistics rows for which the statistics worker cannot/will not
 * compute values (e.g., summary measurements, score).
 */
export const filterComputableStatistics = (stats: StatRow[]): StatRow[] =>
  stats.filter((row) => statisticsRows[row.id]);

/**
 * This method gets called on the initial render or whenever there is a
 * change to the underlying dataset.
 * This usually happens whenever the user sets a filter.
 *
 * It handles the dispatching of stat calculation jobs as well as
 * necessary transformation to bring the calculation results into the
 * required format.
 */
export const computeStats = async ({
  tools,
  tableData,
  stats,
}: {
  tools: Tool[];
  tableData: TableRow[];
  stats: StatRow[];
}): Promise<StatRow[]> => {
  const formatter = buildFormatter(tools);
  let res = await processData({ tools, tableData, formatter });

  const availableStats = stats
    .map((row) => row.id)
    .filter((id): id is StatisticRowId => Boolean(statisticsRows[id]));
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
    const out: Array<Record<string, unknown>> = [];
    const toolColumns = tools[toolIdx]?.columns ?? [];
    let pointer = 0;
    let curr = toolColumns[pointer];

    for (const col of tool) {
      const { title } = col;
      while (pointer < toolColumns.length && title !== curr?.title) {
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

  // Put new statistics in same "shape" as old ones.
  return filterComputableStatistics(stats).map((row) => {
    const content = row.content.map((tool, toolIdx) => {
      const toolCols = res[toolIdx] ?? [];
      return toolCols.map((col) => (col as Record<string, unknown>)[row.id]);
    });
    return { ...row, content };
  });
};

/**
 * Creates a number formatters for each tool and column and
 * configures them with the columns defined number of significant digits
 *
 * @param {object[]} tools
 */
const buildFormatter = (tools: Tool[]): FormatterMatrix =>
  tools.map((tool, tIdx) =>
    tool.columns.map((column, cIdx) => {
      const { number_of_significant_digits: sigDigits } = column;

      // NOTE (JS->TS): The formatter matrix stores builder instances first and
      // later built formatter functions. We cast here to keep the existing
      // matrix-based control flow unchanged.
      return new NumberFormatterBuilder(
        sigDigits,
        `${tIdx}-${cIdx}`,
      ) as unknown as NumberFormatterBuilderLike;
    }),
  );

const maybeRound =
  (key: string, maxDecimalInputLength: number, columnIdx: number) =>
  (
    number: string,
    { significantDigits }: { significantDigits?: number },
  ): string => {
    const asNumber = Number(number);
    const [integer, decimal] = number.split(".");
    void columnIdx;

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
      const sig = Number(significantDigits);
      const deltaSigDigLength = sig - (cleanedInt.length + cleanedDec.length);

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
const cleanupStats = (
  unfilteredStats: unknown[][],
  formatter: FormatterMatrix,
  availableStats: readonly StatisticRowId[],
): Array<Array<Record<string, unknown>>> => {
  const stats = unfilteredStats.map((tool, toolIdx) =>
    (Array.isArray(tool) ? tool : []).map((col, colIdx) => {
      const colRec = asRecord(col) ? col : ({} as Record<string, unknown>);
      const { columnType } = colRec as UnfilteredColumnStats;
      const out: Record<string, unknown> = { columnType };

      for (const visibleStat of availableStats) {
        const currentCol = colRec[visibleStat];
        if (!currentCol) {
          continue;
        }
        out[visibleStat] = currentCol;

        if (
          asRecord(currentCol) &&
          "sum" in currentCol &&
          ((currentCol as ComputedStatEntry).sum ?? false)
        ) {
          const f = formatter[toolIdx]?.[colIdx];

          // NOTE (JS->TS): Added runtime narrowing because formatter cells are a
          // union (builder | built function). Only builder-like cells support addDataItem.
          if (f && typeof f === "object" && "addDataItem" in f) {
            f.addDataItem((currentCol as ComputedStatEntry).sum);
          }
        }
      }
      return out;
    }),
  );

  for (let t = 0; t < formatter.length; t += 1) {
    for (let c = 0; c < (formatter[t]?.length ?? 0); c += 1) {
      const f = formatter[t][c];

      // NOTE (JS->TS): Added runtime narrowing because formatter cells are a
      // union (builder | built function). Only builder-like cells support build().
      if (f && typeof f === "object" && "build" in f) {
        formatter[t][c] = f.build();
      }
    }
  }

  const cleaned = stats.map((tool, toolIdx) =>
    tool
      .map(({ columnType, ...column }, columnIdx) => {
        void columnType;
        const out: Record<string, unknown> = {};
        if ((column as Record<string, unknown>).total === undefined) {
          return undefined;
        }

        for (const [resultKey, result] of Object.entries(column)) {
          const rowRes: Record<string, unknown> = {};
          const resultRec = asRecord(result) ? result : {};
          const meta = asRecord(resultRec.meta)
            ? (resultRec.meta as { maxDecimals?: number })
            : undefined;

          for (const [key, value] of Object.entries(resultRec)) {
            if (keysToIgnore.has(key as "meta")) {
              continue;
            }

            const maxDecimalInputLength = meta?.maxDecimals ?? 0;

            // attach the title to the stat item
            // this will later be used to ensure correct ordering of columns
            if (key === "title") {
              out.title = value;
              continue;
            }

            const valueIsNumberLike =
              !isNil(value) &&
              (typeof value === "number" || typeof value === "string") &&
              (!Number.isNaN(Number(value)) || value === "NaN");

            const fmtCell = formatter[toolIdx]?.[columnIdx];
            if (valueIsNumberLike && typeof fmtCell === "function") {
              try {
                if (key === "sum") {
                  rowRes[key] = fmtCell(value, {
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
                  rowRes[key] = fmtCell(value, {
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
              } catch (e: unknown) {
                console.error({
                  key,
                  value,
                  formatter: fmtCell,
                  e,
                });
              }
            }
          }

          out[resultKey] = rowRes;
        }

        return out;
      })
      .filter((i): i is Record<string, unknown> => !isNil(i)),
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
const classifyResult = (result: unknown): string => {
  if (isNil(result)) {
    return RESULT_CLASS_OTHER;
  }
  if (result === RESULT_TRUE_PROP) {
    return RESULT_CLASS_TRUE;
  }
  if (result === RESULT_FALSE_PROP) {
    return RESULT_CLASS_FALSE;
  }
  if (
    typeof result === "string" &&
    result.startsWith(`${RESULT_FALSE_PROP}(`) &&
    result.endsWith(")")
  ) {
    return RESULT_CLASS_FALSE;
  }

  return RESULT_CLASS_OTHER;
};

const prepareRows = (
  rows: TableRow[],
  toolIdx: number,
  categoryAccessor: (toolIdx: number, row: TableRow) => string,
  statusAccessor: (toolIdx: number, row: TableRow) => string,
  formatter: FormatterMatrix,
): PreppedRow[] => {
  void formatter;
  return rows.map((row) => {
    const cat = categoryAccessor(toolIdx, row);
    const stat = statusAccessor(toolIdx, row);

    const mappedCat = cat.replace(/-/g, "_");
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
const splitColumnsWithMeta =
  (tools: Tool[]) =>
  (preppedRows: PreppedRow[], toolIdx: number): SplitColumnItem[][] => {
    const out: SplitColumnItem[][] = [];
    for (const { row, categoryType, resultType } of preppedRows) {
      for (const columnIdx in row) {
        const cIdx = Number(columnIdx);
        const rawCell = row[cIdx];
        const column = rawCell?.raw;
        const curr = out[cIdx] || [];
        // we attach extra meta information for later use in calculation and mapping
        // of results
        const { type: columnType, title: columnTitle } =
          tools[toolIdx].columns[cIdx];

        curr.push({
          categoryType,
          resultType,
          column,
          columnType,
          columnTitle,
        });
        out[cIdx] = curr;
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
const processData = async ({
  tools,
  tableData,
  formatter,
}: {
  tools: Tool[];
  tableData: TableRow[];
  formatter: FormatterMatrix;
}): Promise<unknown[][]> => {
  const catAccessor = (toolIdx: number, row: TableRow) =>
    row.results[toolIdx].category;
  const statAccessor = (toolIdx: number, row: TableRow) =>
    row.results[toolIdx].values[0].raw;
  const promises: Array<Array<Promise<unknown>>> = [];

  const splitRows: PreppedRow[][] = [];
  for (const toolIdx in tools) {
    const tIdx = Number(toolIdx);

    // NOTE (JS->TS): Convert for..in string keys to numbers for safe array indexing.
    splitRows.push(
      prepareRows(tableData, tIdx, catAccessor, statAccessor, formatter),
    );
  }
  const columnSplitter = splitColumnsWithMeta(tools);

  const preparedData = splitRows.map((rows, idx) => columnSplitter(rows, idx));
  // filter out non-relevant rows
  for (const toolIdx in preparedData) {
    const tIdx = Number(toolIdx);

    // NOTE (JS->TS): Convert for..in string keys to numbers for safe array indexing.
    preparedData[tIdx] = preparedData[tIdx].filter((i) => !isNil(i));
  }

  for (const toolDataIdx in preparedData) {
    const tIdx = Number(toolDataIdx);
    const toolData = preparedData[tIdx];
    const subPromises: Array<Promise<unknown>> = [];
    for (const columnIdx in toolData) {
      const cIdx = Number(columnIdx);

      // NOTE (JS->TS): Convert for..in string keys to numbers for safe array indexing.
      const columns = toolData[cIdx];
      subPromises.push(
        enqueue({ name: "stats", data: columns }) as Promise<unknown>,
      );
    }
    promises[tIdx] = subPromises;
  }

  const allPromises = promises.map((p) => Promise.all(p));
  const res = await Promise.all(allPromises);

  return res;
};
