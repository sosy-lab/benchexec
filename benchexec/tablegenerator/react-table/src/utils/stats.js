import { isNil, NumberFormatterBuilder } from "./utils";
import { enqueue } from "../workers/workerDirector";

export const buildFormatter = (tools) =>
  tools.map((tool, tIdx) =>
    tool.columns.map((column, cIdx) => {
      const { number_of_significant_digits: sigDigits } = column;
      return new NumberFormatterBuilder(sigDigits, `${tIdx}-${cIdx}`);
    }),
  );

export const cleanupStats = (stats, formatter) => {
  const cleaned = stats.map((tool, toolIdx) =>
    tool
      .map((column, columnIdx) => {
        const out = {};
        if (column.total === undefined) {
          return undefined;
        }
        for (const [resultKey, result] of Object.entries(column)) {
          const rowRes = {};

          for (let [key, value] of Object.entries(result)) {
            if (key === "title") {
              out.title = value;
              continue;
            }
            if (
              !isNil(value) &&
              !isNaN(value) &&
              formatter[toolIdx][columnIdx]
            ) {
              try {
                if (key === "sum") {
                  rowRes[key] = formatter[toolIdx][columnIdx](value, {
                    leadingZero: false,
                    whitespaceFormat: true,
                    html: true,
                  });
                } else {
                  rowRes[key] = formatter[toolIdx][columnIdx](value, {
                    leadingZero: true,
                    whitespaceFormat: false,
                    html: false,
                  });
                }
              } catch (e) {
                console.error({
                  key,
                  value,
                  formatter: formatter[toolIdx][columnIdx][key],
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

    for (const colIdx in row.results[toolIdx].values) {
      const { raw } = row.results[toolIdx].values[colIdx];
      if (!isNaN(Number(raw))) {
        formatter[toolIdx][colIdx].addDataItem(raw);
      }
    }

    return {
      categoryType: mappedCat,
      resultType: mappedRes,
      row: row.results[toolIdx].values,
    };
  });
};

export const splitColumnsWithMeta = (tools) => (preppedRows, toolIdx) => {
  const out = [];
  for (const { row, categoryType, resultType } of preppedRows) {
    for (const columnIdx in row) {
      const column = row[columnIdx].raw;
      const curr = out[columnIdx] || [];
      const { type: columnType, title: columnTitle } = tools[toolIdx].columns[
        columnIdx
      ];

      curr.push({ categoryType, resultType, column, columnType, columnTitle });
      out[columnIdx] = curr;
    }
  }
  return out;
};

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

  for (const to in formatter) {
    for (const co in formatter[to]) {
      formatter[to][co] = formatter[to][co].build();
    }
  }

  const cleaned = cleanupStats(res, formatter);
  return cleaned;
};
