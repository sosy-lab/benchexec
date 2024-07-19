// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import React, { useState, useMemo, useEffect } from "react";

import {
  useTable,
  useFilters,
  useResizeColumns,
  useFlexLayout,
} from "react-table";
import { useSticky } from "react-table-sticky";
import {
  createRunSetColumns,
  SelectColumnsButton,
  StandardColumnHeader,
} from "./TableComponents";
import { computeStats, statisticsRows } from "../utils/stats.js";
import {
  determineColumnWidth,
  isNumericColumn,
  isNil,
  getHiddenColIds,
} from "../utils/utils";
import { BenchmarkSetupRow } from "./Summary.js";

const isTestEnv = process.env.NODE_ENV === "test";

const titleColWidth = window.innerWidth * 0.15;

const renderTooltip = (cell) =>
  Object.keys(cell)
    .filter((key) => cell[key] && key !== "sum")
    .map((key) => `${key}: ${cell[key]}`)
    .join(", ") || undefined;

const StatisticsTable = ({
  selectColumn,
  tools,
  switchToQuantile,
  hiddenCols,
  tableData,
  onStatsReady,
  stats: defaultStats,
  filtered = false,
  benchmarkSetupData,
}) => {
  // We want to skip stat calculation in a test environment if not
  // specifically wanted (signaled by a passed onStatsReady callback function)
  const skipStats = isTestEnv && !onStatsReady;

  // When filtered, initialize with empty statistics until computed statistics
  // are available in order to prevent briefly showing the wrong statistics.
  const [stats, setStats] = useState(filtered ? [] : defaultStats);
  const [isTitleColSticky, setTitleColSticky] = useState(true);

  // we want to trigger a re-calculation of our stats whenever data changes.
  useEffect(() => {
    const updateStats = async () => {
      if (filtered) {
        const newStats = await computeStats({
          tools,
          tableData,
          stats: defaultStats,
        });
        setStats(newStats);
      } else {
        setStats(defaultStats);
      }
      if (onStatsReady) {
        onStatsReady();
      }
    };
    if (!skipStats) {
      updateStats(); // necessary such that hook is not async
    }
  }, [tools, tableData, onStatsReady, skipStats, defaultStats, filtered]);

  /**
   * Render the table header. It can display two kinds of header groups:
   * 1. Toolset Header Group: includes the toolset names. It has the type "toolset".
   * 2. Columns Header Group: includes the column names. It has the type "columns".
   * @param {*} headerGroup The header group to render
   * @param {string} type The type of the header group. Can be "toolset" or "columns".
   * @returns {JSX.Element}
   */
  const renderTableHeader = (headerGroup, type) => (
    <div className="table-header">
      <div className="tr headergroup" {...headerGroup.getHeaderGroupProps()}>
        {headerGroup.headers.map((header) => (
          <div
            {...header.getHeaderProps({
              className: `th header ${header.headers ? "outer " : ""}${
                header.className || ""
              }`,
            })}
          >
            {header.render("Header")}
            {(!header.className || !header.className.includes("separator")) && (
              <div
                {...header.getResizerProps()}
                className={`resizer ${header.isResizing ? "isResizing" : ""}`}
              />
            )}
          </div>
        ))}
      </div>
    </div>
  );

  /**
   * Render the table data rows.
   * These rows contain the statistics data that is the bottom part of the table.
   * @param {*} rows The rows to render
   * @returns {JSX.Element}
   */
  const renderTableDataRows = (rows) => (
    <div {...getTableBodyProps()} className="table-body body">
      {rows.map((row) => {
        prepareRow(row);
        console.log("Row Values: ", row.values);
        return (
          <div {...row.getRowProps()} className="tr">
            {row.cells.map((cell) => (
              <div
                {...cell.getCellProps({
                  className: "td " + (cell.column.className || ""),
                })}
              >
                {cell.render("Cell")}
              </div>
            ))}
          </div>
        );
      })}
    </div>
  );

  /**
   * Render the benchmark setup row.
   * @param {*} row The row to render
   * @returns {JSX.Element}
   */
  const renderBenchmarkSetupRows = (rows) => {
    // return rows.map((row) => (
    //   <div key={"tr-" + row.id} className="tr" {...row.getRowProps()}>
    //     <th key={"td-" + row.id}>{row.name}</th>
    //     {row.content.map((tool, j) => (
    //       <BenchmarkSetupRow
    //         key={"td-" + row.id + "-" + j}
    //         row={row.id}
    //         data={tool[0]}
    //         colSpan={tool[1]}
    //         index={j}
    //       />
    //     ))}
    //   </div>
    // ));

    return rows.map((row) => {
      prepareRow(row);
      console.log("Benchmark Setup Row : ", row);
      console.log("Benchmark Setup Row Original: ", row.original.content);
      return (
        <div {...row.getRowProps()} className="tr">
          {row.cells.map((cell) => (
            <div
              {...cell.getCellProps({
                className: "td " + (cell.column.className || ""),
              })}
            >
              {cell.column.id.includes("summary") ||
              cell.column.id.includes("summary") ? (
                cell.render("Cell")
              ) : (
                <div className="cell">Testing</div>
              )}
            </div>
          ))}
        </div>
      );
    });
  };

  const renderTable = (headerGroups, rows) => {
    if (filtered && stats.length === 0) {
      return (
        <p id="statistics-placeholder">
          Please wait while the statistics are being calculated.
        </p>
      );
    }

    if (headerGroups.length !== 2)
      throw new Error(
        `Unexpected number of header groups. Expected 2 (1 for toolset, 1 for statistics columns). Got ${headerGroups.length}.`,
      );

    const [toolsetNameHeaderGroup, columnsHeaderGroup] = headerGroups;
    const benchmarkSetupData = rows.filter(
      (row) => row.original.type === "benchmark_setup",
    );
    const statsData = rows.filter((row) => row.original.type === "statistics");

    return (
      <div id="statistics-table">
        <div className="table sticky">
          <div className="table-content">
            <div className="table-container" {...getTableProps()}>
              {renderTableHeader(toolsetNameHeaderGroup, "toolset")}
              {renderBenchmarkSetupRows(benchmarkSetupData)}
              {renderTableHeader(columnsHeaderGroup, "columns")}
              {renderTableDataRows(statsData)}
            </div>
          </div>
        </div>
      </div>
    );
  };

  const columns = useMemo(() => {
    const createColumnBuilder =
      ({ switchToQuantile, hiddenCols }) =>
      (runSetIdx, column, columnIdx) => ({
        id: `${runSetIdx}_${column.display_title}_${columnIdx}`,
        Header: (
          <StandardColumnHeader
            column={column}
            className="header-data clickable"
            title="Show Quantile Plot of this column"
            onClick={(_) => switchToQuantile(column)}
          />
        ),
        hidden:
          hiddenCols[runSetIdx].includes(column.colIdx) ||
          !(isNumericColumn(column) || column.type === "status"),
        width: determineColumnWidth(
          column,
          null,
          column.type === "status" ? 6 : null,
        ),
        minWidth: 30,
        accessor: (row) =>
          row.type === "statistics"
            ? row.content[runSetIdx][columnIdx]
            : row.content,
        Cell: (cell) => {
          let valueToRender = cell.value?.sum;
          if (column.type === "status") {
            // We handle status differently as the main aggregation (denoted "sum")
            // is of type "count" for this column type.
            // This means that the default value if no data is available is 0
            if (cell.value === undefined) {
              // No data is available, default to 0
              valueToRender = 0;
            } else if (cell.value === null) {
              // We receive a null value directly from the stats object of the dataset.
              // Will be rendered as "-"
              // This edge case only applies to the local summary as it includes static values
              // that we can not calculate and therefore directly take them from the stats object.

              valueToRender = null;
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
              title={
                column.type !== "status" ? renderTooltip(cell.value) : undefined
              }
            ></div>
          ) : (
            <div className="cell">-</div>
          );
        },
      });

    const createRowTitleColumn = () => ({
      Header: () => (
        <form>
          <label title="Fix the first column">
            Fixed row title:
            <input
              id="fixed-row-title"
              name="fixed"
              type="checkbox"
              checked={isTitleColSticky}
              onChange={({ target }) => setTitleColSticky(target.checked)}
            />
          </label>
        </form>
      ),
      id: "row-title",
      sticky: isTitleColSticky ? "left" : "",
      width: titleColWidth,
      minWidth: 100,
      columns: [
        {
          id: "summary",
          width: titleColWidth,
          minWidth: 100,
          Header: <SelectColumnsButton handler={selectColumn} />,
          enableColSpan: true,
          Cell: (cell) =>
            cell.row.original.type === "benchmark_setup" ? (
              <>{cell.row.original.name}</>
            ) : (
              <div
                dangerouslySetInnerHTML={{
                  __html:
                    (cell.row.original.title ||
                      "&nbsp;".repeat(
                        4 * statisticsRows[cell.row.original.id].indent,
                      ) + statisticsRows[cell.row.original.id].title) +
                    (filtered ? " of selected rows" : ""),
                }}
                title={
                  cell.row.original.description ||
                  statisticsRows[cell.row.original.id].description
                }
                className="row-title"
              />
            ),
        },
      ],
    });

    const statColumns = tools
      .map((runSet, runSetIdx) =>
        createRunSetColumns(
          runSet,
          runSetIdx,
          createColumnBuilder({ switchToQuantile, hiddenCols }),
        ),
      )
      .flat();

    return [createRowTitleColumn()].concat(statColumns);
  }, [
    filtered,
    isTitleColSticky,
    switchToQuantile,
    hiddenCols,
    selectColumn,
    tools,
  ]);

  /** The data for the table is a combination of the benchmark setup data and the statistics data
   * Each row is tagged with a type to distinguish between the two.
   * type: "benchmark_setup" | "statistics"
   * The benchmark rows are displayed first followed by the statistics rows.
   * */
  const data = useMemo(() => {
    return [
      ...benchmarkSetupData.map((b) => ({
        type: "benchmark_setup",
        ...b,
      })),
      ...stats.map((s) => ({
        type: "statistics",
        ...s,
      })),
    ];
  }, [stats, benchmarkSetupData]);

  console.log("Data", data);

  const { getTableProps, getTableBodyProps, headerGroups, rows, prepareRow } =
    useTable(
      {
        columns,
        data,
        initialState: {
          hiddenColumns: getHiddenColIds(columns),
        },
      },
      useFilters,
      useResizeColumns,
      useFlexLayout,
      useSticky,
    );

  return (
    <div id="statistics">
      <h2>Statistics</h2>
      {renderTable(headerGroups, rows)}
    </div>
  );
};

export default StatisticsTable;
