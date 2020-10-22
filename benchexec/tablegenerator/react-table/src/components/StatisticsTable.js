// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import React, { useState, useCallback, useEffect, useRef } from "react";
import withFixedColumns from "react-table-hoc-fixed-columns";
import ReactTable from "react-table";
import {
  createRunSetColumns,
  SelectColumnsButton,
  StandardColumnHeader,
} from "./TableComponents";
import { buildFormatter, processData } from "../utils/stats.js";
import { determineColumnWidth, isNumericColumn, isNil } from "../utils/utils";

const isTestEnv = process.env.NODE_ENV === "test";

const ReactTableFixedColumns = withFixedColumns(ReactTable);

const createRowTitleColumn = ({
  selectColumn,
  fixed,
  handleInputChange,
  headerWidth,
}) => ({
  Header: () => (
    <div className="toolsHeader">
      <form>
        <label title="Fix the first column">
          Fixed row title:
          <input
            id="fixed-row-title"
            name="fixed"
            type="checkbox"
            checked={fixed}
            onChange={handleInputChange}
          />
        </label>
      </form>
    </div>
  ),
  fixed: fixed ? "left" : "",
  minWidth: headerWidth,
  columns: [
    {
      id: "summary",
      minWidth: headerWidth,
      Header: <SelectColumnsButton handler={selectColumn} />,
      accessor: "",
      Cell: (cell) => (
        <div
          dangerouslySetInnerHTML={{ __html: cell.value.title }}
          title={cell.value.description}
          className="row-title"
        />
      ),
    },
  ],
});

const renderTooltip = (cell) =>
  Object.keys(cell)
    .filter((key) => cell[key] && key !== "sum")
    .map((key) => `${key}: ${cell[key]}`)
    .join(", ") || undefined;

const createColumnBuilder = ({ changeTab, hiddenCols }) => (
  runSetIdx,
  column,
  columnIdx,
) => ({
  id: `${runSetIdx}_${column.display_title}_${columnIdx}`,
  Header: (
    <StandardColumnHeader
      column={column}
      className="columns"
      title="Show Quantile Plot of this column"
      onClick={(e) => changeTab(e, column, 2)}
    />
  ),
  show:
    !hiddenCols[runSetIdx].includes(columnIdx) &&
    (isNumericColumn(column) || column.type === "status"),
  minWidth: determineColumnWidth(
    column,
    null,
    column.type === "status" ? 6 : null,
  ),
  accessor: (row) => row.content[runSetIdx][columnIdx],
  Cell: (cell) =>
    !isNil(cell.value) ? (
      <div
        dangerouslySetInnerHTML={{
          __html:
            column.type === "status" && Number.isInteger(Number(cell.value.sum))
              ? Number(cell.value.sum)
              : cell.value.sum,
        }}
        className="cell"
        title={column.type !== "status" ? renderTooltip(cell.value) : undefined}
      ></div>
    ) : (
      <div className="cell">-</div>
    ),
});

const transformStatsFromWorkers = ({ newStats, stats, setStats }) => {
  // our stats template to steal from

  const selector = {
    0: "total",
    2: "correct-total",
    3: "correct-true",
    4: "correct-false",
    5: "wrong-total",
    6: "wrong-true",
    7: "wrong-false",
  };
  const templ = stats;

  const transformed = templ.map((row, rowIdx) => {
    row.content = row.content.map((tool, toolIdx) => {
      const key = selector[rowIdx];
      if (!key || !newStats[toolIdx]) {
        return tool;
      }
      return newStats[toolIdx].map((col) => col[key]);
    });
    return row;
  });

  setStats(transformed);
};

const updateStats = async ({
  tools,
  data: table,
  onStatsReady,
  skipStats,
  stats,
  setStats,
}) => {
  const formatter = buildFormatter(tools);
  let res = skipStats ? {} : await processData({ tools, table, formatter });
  // fill up stat array to match column mapping

  res = res.map((tool, toolIdx) => {
    const out = [];
    const toolColumns = tools[toolIdx].columns;
    let pointer = 0;
    let curr = toolColumns[pointer];

    for (const col of tool) {
      const { title } = col;
      while (pointer < toolColumns.length && title !== curr.title) {
        out.push({});
        pointer++;
        curr = toolColumns[pointer];
      }
      if (pointer >= toolColumns.length) {
        break;
      }
      out.push(col);
      pointer++;
      curr = toolColumns[pointer];
    }

    return out;
  });

  transformStatsFromWorkers({ newStats: res, stats, setStats });

  if (onStatsReady) {
    console.log("calling onStatsReady");
    onStatsReady();
  } else {
    console.log("onStatsReady not found");
  }
};

export default ({
  width,
  selectColumn,
  tools,
  changeTab,
  hiddenCols,
  data,
  onStatsReady,
  headerWidth,
  stats: defaultStats,
}) => {
  const skipStats = isTestEnv && !onStatsReady;

  const [fixed, setFixed] = useState(true);
  const [stats, setStats] = useState(defaultStats);
  const statRef = useRef(stats);

  const handleInputChange = ({ target }) => setFixed(target.checked);

  const createColumn = useCallback(
    createColumnBuilder({ changeTab, hiddenCols }),
    [changeTab, hiddenCols],
  );

  useEffect(() => {
    updateStats({
      tools,
      data,
      onStatsReady,
      skipStats,
      stats: statRef.current,
      setStats,
    });
  }, [tools, data, onStatsReady, skipStats, statRef]);

  const statColumns = tools
    .map((runSet, runSetIdx) =>
      createRunSetColumns(runSet, runSetIdx, createColumn),
    )
    .flat();

  return (
    <div id="statistics">
      <h2>Statistics</h2>
      <ReactTableFixedColumns
        data={stats}
        columns={[
          createRowTitleColumn({
            fixed,
            selectColumn,
            headerWidth,
            handleInputChange,
          }),
        ].concat(statColumns)}
        showPagination={false}
        className="-highlight"
        minRows={0}
        sortable={false}
        width={width}
      />
    </div>
  );
};
