// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0
import React, { useState, useMemo } from "react";
import {
  createRunSetColumns,
  StandardColumnHeader,
  SelectColumnsButton,
} from "./TableComponents.js";
import {
  determineColumnWidth,
  isNumericColumn,
  getHiddenColIds,
} from "../utils/utils";
import {
  useTable,
  useFilters,
  useResizeColumns,
  useFlexLayout,
} from "react-table";
import { useSticky } from "react-table-sticky";

const infos = [
  "displayName",
  "tool",
  "limit",
  "host",
  "os",
  "system",
  "date",
  "runset",
  "branch",
  "options",
  "property",
];
const titleColWidth = window.innerWidth * 0.15;

const Summary = (props) => {
  const [isTitleColSticky, setTitleColSticky] = useState(true);

  /* ++++++++++++++ Helper functions ++++++++++++++ */

  const renderOptions = (text) => {
    return text.split(/[\s]+-/).map((option, i) => (
      <li key={option}>
        <code>{i === 0 ? option : `-${option}`}</code>
      </li>
    ));
  };

  const renderTooltip = (cell) =>
    Object.keys(cell)
      .filter((key) => cell[key] && key !== "sum")
      .map((key) => `${key}: ${cell[key]}`)
      .join(", ") || undefined;

  /* ++++++++++++++ Table render functions ++++++++++++++ */

  const renderEnvironmentRow = (row, text, colSpan, j) => {
    const isOptionRow = row === "options";
    return (
      <td
        colSpan={colSpan}
        key={text + j}
        className={`header__tool-row${isOptionRow && " options"}`}
      >
        {isOptionRow ? <ul>{renderOptions(text)}</ul> : text}
      </td>
    );
  };

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

              <div
                {...header.getResizerProps()}
                className={`resizer ${header.isResizing ? "isResizing" : ""}`}
              />
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
    return (
      <div className="main-table">
        <div id="statistic-table" className="table sticky" {...getTableProps()}>
          <div className="table-content">
            {renderTableHeaders(headerGroups)}
            {renderTableData(rows)}
          </div>
          <div className="-loading"></div>
        </div>
      </div>
    );
  };

  const { switchToQuantile, hiddenCols, selectColumn, tools } = props;
  const columns = useMemo(() => {
    const createColumn = (runSetIdx, column, columnIdx) => ({
      id: `${runSetIdx}_${column.display_title}_${columnIdx}`,
      Header: (
        <StandardColumnHeader
          column={column}
          className="header-data"
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
      Cell: (cell) =>
        cell.value ? (
          <div
            dangerouslySetInnerHTML={{ __html: cell.value.sum }}
            className="cell"
            title={renderTooltip(cell.value)}
          ></div>
        ) : (
          <div className="cell">-</div>
        ),
    });

    const createRowTitleColumn = () => ({
      Header: () => (
        <div className="toolsHeader">
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
        </div>
      ),
      id: "row-title",
      fixed: isTitleColSticky ? "left" : "",
      width: titleColWidth,
      minWidth: 100,
      columns: [
        {
          id: "summary",
          className: "select-column-header",
          width: titleColWidth,
          minWidth: 100,
          Header: <SelectColumnsButton handler={selectColumn} />,
          Cell: (cell) => (
            <div
              dangerouslySetInnerHTML={{ __html: cell.row.original.title }}
              title={cell.row.original.description}
              className="row-title"
            />
          ),
        },
      ],
    });

    const statColumns = tools
      .map((runSet, runSetIdx) =>
        createRunSetColumns(runSet, runSetIdx, createColumn),
      )
      .flat();

    return [createRowTitleColumn()].concat(statColumns);
  }, [isTitleColSticky, switchToQuantile, hiddenCols, selectColumn, tools]);

  const data = useMemo(() => props.tableData, [props.tableData]);

  const {
    getTableProps,
    getTableBodyProps,
    headerGroups,
    rows,
    prepareRow,
  } = useTable(
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
    <div id="summary">
      <div id="benchmark_setup">
        <h2>Benchmark Setup</h2>
        <table>
          <tbody>
            {infos
              .map((row) => props.tableHeader[row])
              .filter((row) => row !== null)
              .map((row, i) => (
                <tr key={"tr-" + row.id} className={row.id}>
                  <th key={"td-" + row.id}>{row.name}</th>
                  {row.content.map((tool, j) =>
                    renderEnvironmentRow(row.id, tool[0], tool[1], j),
                  )}
                </tr>
              ))}
          </tbody>
        </table>
      </div>
      <div id="statistics">
        <h2>Statistics</h2>
        {renderTable(headerGroups, rows)}
      </div>
      <p>
        Generated by{" "}
        <a
          className="link"
          href="https://github.com/sosy-lab/benchexec"
          target="_blank"
          rel="noopener noreferrer"
        >
          {" "}
          BenchExec {props.version}
        </a>
      </p>
    </div>
  );
};

export default Summary;
