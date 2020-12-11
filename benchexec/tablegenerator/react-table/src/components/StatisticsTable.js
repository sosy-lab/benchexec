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
  Cell: (cell) => {
    let valueToRender = cell.value?.sum;
    if (column.type === "status") {
      // As the main aggregation for the status columns is count (vs sum)
      // we default to zero, if we don't have any results for the cell
      if (isNil(cell.value)) {
        valueToRender = 0;
      } else {
        valueToRender = Number.isInteger(Number(cell.value.sum))
          ? Number(cell.value.sum)
          : cell.value.sum;
      }
    }
    return !isNil(valueToRender) ? (
      <div
        dangerouslySetInnerHTML={{
          __html: valueToRender,
        }}
        className="cell"
        title={column.type !== "status" ? renderTooltip(cell.value) : undefined}
      ></div>
    ) : (
      <div className="cell">-</div>
    );
  },
});

const transformStatsFromWorkers = ({ newStats, stats, setStats }) => {
  // our stats template to steal from

  const selector = {
    total: "total",
    "correct results": "correct-total",
    "correct true": "correct-true",
    "correct false": "correct-false",
    "incorrect results": "wrong-total",
    "incorrect true": "wrong-true",
    "incorrect false": "wrong-false",
  };
  const templ = stats;

  // we currently only handle the cases that are described in "selector"
  // for now, we want to skip all other cases and take them from the original stats
  const transformed = templ.map((row) => {
    const title = row.title.replace(/&nbsp;/g, "");
    row.content = row.content.map((tool, toolIdx) => {
      const key = selector[title];
      if (!key || !newStats[toolIdx]) {
        return tool;
      }
      return newStats[toolIdx].map((col) => col[key]);
    });
    return row;
  });

  setStats(transformed);
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

  // The result of our stat calculation only contains relevant columns.
  // The stat table however requires a strict ordering of columns that also
  // includes columns that are not even rendered.
  //
  // In order to ensure a consistent layout we iterate through all columns
  // of the runset and append dummy objects until we reach a column that we
  // have calculated data for
  res = res.map((tool, toolIdx) => {
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

  transformStatsFromWorkers({ newStats: res, stats, setStats });

  if (onStatsReady) {
    console.log("calling onStatsReady");
    // calling onStatsReady callback if available
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
  // We want to skip stat calculation in a test environment if not
  // specifically wanted (signaled by a passed onStatsReady callback function)
  const skipStats = isTestEnv && !onStatsReady;

  const [fixed, setFixed] = useState(true);
  const [stats, setStats] = useState(defaultStats);

  // we wrap stats in a ref to mitigate unwanted re-renders
  const statRef = useRef(stats);

  const handleInputChange = ({ target }) => setFixed(target.checked);

  const createColumn = useCallback(
    createColumnBuilder({ changeTab, hiddenCols }),
    [changeTab, hiddenCols],
  );

  // we want to trigger a re-calculation of our stats whenever data changes.
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
