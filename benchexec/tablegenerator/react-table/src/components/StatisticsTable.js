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

  const renderTableHeaders = (headerGroups) => (
    <div className="table-header">
      {headerGroups.map((headerGroup) => (
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

              {(!header.className ||
                !header.className.includes("separator")) && (
                <div
                  {...header.getResizerProps()}
                  className={`resizer ${header.isResizing ? "isResizing" : ""}`}
                />
              )}
            </div>
          ))}
        </div>
      ))}
    </div>
  );

  const renderTableData = (rows) => (
    <div {...getTableBodyProps()} className="table-body body">
      {rows.map((row) => {
        prepareRow(row);
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

  const renderTable = (headerGroups, rows) => {
    if (filtered && stats.length === 0) {
      return (
        <p id="statistics-placeholder">
          Please wait while the statistics are being calculated.
        </p>
      );
    }
    return (
      <div id="statistics-table">
        <div className="table sticky">
          <div className="table-content">
            <div className="table-container" {...getTableProps()}>
              {renderTableHeaders(headerGroups)}
              {renderTableData(rows)}
            </div>
            <div className="-loading"></div>
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
            onClick={(e) => switchToQuantile(column)}
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
        accessor: (row) => row.content[runSetIdx][columnIdx],
        Cell: (cell) => {
          let valueToRender = cell.value?.sum;
          // We handle status differently as the main aggregation (denoted "sum")
          // is of type "count" for this column type.
          // This means that the default value if no data is available is 0
          if (column.type === "status") {
            if (cell.value === undefined) {
              // No data is available, default to 0
              valueToRender = 0;
            } else if (cell.value === null) {
              // We receive a null value directly from the stats object of the dataset.
              // Will be rendered as "-"
              // This edge case only applies to the local summary as it contains static values
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
          Cell: (cell) => (
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
                statisticsRows[cell.row.original.id].description ||
                ""
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

  const data = useMemo(() => stats, [stats]);

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
