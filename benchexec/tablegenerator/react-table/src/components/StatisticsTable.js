// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import React, { useMemo } from "react";
import {
  useFilters,
  useFlexLayout,
  useResizeColumns,
  useTable,
} from "react-table";
import { StandardColumnHeader } from "./TableComponents";
import { useSticky } from "react-table-sticky";
import {
  isNil,
  isNumericColumn,
  getHiddenColIds,
  determineColumnWidth,
} from "../utils/utils";

const renderTooltip = (cell) =>
  Object.keys(cell)
    .filter((key) => cell[key] && key !== "sum")
    .map((key) => `${key}: ${cell[key]}`)
    .join(", ") || undefined;

const StatisticsTable = ({ switchToQuantile, tableData, hiddenCols }) => {
  const { runSet, runSetStats, runSetIndex } = tableData;

  const columns = useMemo(() => {
    const createColumnBuilder =
      ({ switchToQuantile }) =>
      (column, columnIdx) => ({
        id: `${runSetIndex}_${column.display_title}_${columnIdx}`,
        Header: (
          <StandardColumnHeader
            column={column}
            className="header-data clickable"
            title="Show Quantile Plot of this column"
            style={{
              cursor: "pointer",
              padding: 0,
              margin: 0,
              alignContent: "center",
              alignItems: "center",
              backgroundColor: "#EEE",
            }}
            onClick={(_) => switchToQuantile(column)}
          />
        ),
        hidden:
          hiddenCols[runSetIndex].includes(columnIdx) ||
          !(isNumericColumn(column) || column.type === "status"),
        width: determineColumnWidth(
          column,
          null,
          column.type === "status" ? 6 : null,
        ),
        minWidth: 30,
        accessor: (row) => {
          return row.content[runSetIndex][columnIdx];
        },
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
            />
          ) : (
            <div className="cell">-</div>
          );
        },
      });
    const statColumns = runSet.columns
      .map((column, columnIdx) =>
        createColumnBuilder({ switchToQuantile })(column, columnIdx),
      )
      .flat();

    return statColumns;
  }, [switchToQuantile, runSet, runSetIndex, hiddenCols]);

  const data = useMemo(() => runSetStats, [runSetStats]);

  const renderTableHeaders = (headerGroups) => (
    <div className="table-header">
      {headerGroups.map((headerGroup) => (
        <div className="tr headergroup" {...headerGroup.getHeaderGroupProps()}>
          {headerGroup.headers.map((header, index) => (
            <div
              {...header.getHeaderProps({
                className: `th header ${header.headers ? "outer " : ""}${
                  header.className || ""
                }`,
                style: {
                  margin: 0,
                  padding: 0,
                  borderLeft: index !== 0 ? "1px solid #CCC" : "none",
                  borderRight:
                    index !== headerGroup.headers.length - 1
                      ? "1px solid #CCC"
                      : "none",
                  height: "3rem",
                },
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
                  style: {
                    height: "2.3rem",
                    borderTop: "1px solid #DDD",
                  },
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
    return (
      <div id="statistics-table">
        <div className="table sticky">
          <div className="table-content">
            <div className="table-container" {...getTableProps()}>
              {renderTableHeaders(headerGroups)}
              {renderTableData(rows)}
            </div>
          </div>
        </div>
      </div>
    );
  };

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
  return <div id="statistics">{renderTable(headerGroups, rows)}</div>;
};

export default StatisticsTable;
