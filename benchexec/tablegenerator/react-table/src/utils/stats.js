import { isNil, NumberFormatterBuilder, identity } from "./utils";
import { enqueue } from "../workers/workerDirector";

export const buildFormatter = (tools, types) =>
  tools.map((tool) =>
    tool.columns.map((column) => {
      const out = {};

      const { number_of_significant_digits: sigDigits } = column;

      let formatter;
      if (sigDigits) {
        formatter = new NumberFormatterBuilder(sigDigits);
      } else {
        formatter = identity;
      }
      return formatter;
      for (const type of types) {
        out = formatter;
      }
      return out;
    }),
  );

export const cleanupStats = (stats, formatter) => {
  stats.forEach((tool, toolIdx) =>
    tool.forEach((column, columnIdx) => {
      for (const result of Object.values(column)) {
        for (const [type, value] of Object.entries(result)) {
          if (
            !isNil(value) &&
            !isNaN(value) &&
            formatter[toolIdx][columnIdx] &&
            formatter[toolIdx][columnIdx].addDataItem
          ) {
            formatter[toolIdx][columnIdx].addDataItem(value.toString());
          }
        }
      }
    }),
  );

  for (const to in formatter) {
    for (const co in formatter[to]) {
      if (formatter[to][co].build) {
        formatter[to][co] = formatter[to][co].build();
      }
    }
  }

  return stats.map((tool, toolIdx) =>
    tool.map((column, columnIdx) => {
      const out = {};
      for (const [resultKey, result] of Object.entries(column)) {
        const rowRes = {};

        for (const [key, value] of Object.entries(result)) {
          if (!isNil(value) && !isNaN(value) && formatter[toolIdx][columnIdx]) {
            try {
              rowRes[key] = formatter[toolIdx][columnIdx](value, {
                leadingZero: key !== "sum",
                whitespaceFormat: true,
                html: true,
              });
            } catch (e) {
              console.error({
                key,
                value,
                formatter: formatter[toolIdx][columnIdx],
              });
            }
          }
        }

        out[resultKey] = rowRes;
      }

      return out;
    }),
  );
};

export const prepareRows = (
  rows,
  toolIdx,
  categoryAccessor,
  statusAccessor,
) => {
  const categoryMapping = {
    correct: "correct",
    "correct-unconfirmed": "correctUnconfirmed",
    wrong: "wrong",
    unknown: "unknown",
    error: "error",
    missing: "missing",
  };

  const resultMapping = {
    true: "true",
    false: "false",
  };

  return rows.map((row) => {
    const cat = categoryAccessor(toolIdx, row);
    const stat = statusAccessor(toolIdx, row);

    const mappedCat = categoryMapping[cat] || "other";
    const mappedRes = resultMapping[stat] || "other";

    return {
      categoryType: mappedCat,
      resultType: mappedRes,
      row: row.results[toolIdx].values,
    };
  });
};

export const splitColumnsWithMeta = (preppedRows) => {
  const out = [];
  for (const { row, categoryType, resultType } of preppedRows) {
    for (const columnIdx in row) {
      const column = Number(row[columnIdx].raw) || undefined;
      const curr = out[columnIdx] || [];
      curr.push({ categoryType, resultType, column });
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
    splitRows.push(prepareRows(table, toolIdx, catAccessor, statAccessor));
  }

  const preparedData = splitRows.map(splitColumnsWithMeta);

  for (const toolDataIdx in preparedData) {
    const toolData = preparedData[toolDataIdx];
    const subPromises = [];
    for (const columns of toolData) {
      subPromises.push(enqueue({ name: "stats", data: columns }));
    }
    promises[toolDataIdx] = subPromises;
  }

  const allPromises = promises.map((p) => Promise.all(p));
  const res = await Promise.all(allPromises);
  console.log(`Calculation took ${Date.now() - start}ms`);

  const cleaned = cleanupStats(res, formatter);
  return cleaned;
};
