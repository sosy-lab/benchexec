// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import React from "react";
import ReactTable from "react-table";
import "react-table/react-table.css";
import withFixedColumns from "react-table-hoc-fixed-columns";
import "react-table-hoc-fixed-columns/lib/styles.css";
import {
  createRunSetColumns,
  StandardColumnHeader,
  SelectColumnsButton,
} from "./TableComponents.js";
import { determineColumnWidth, isNumericColumn } from "../utils/utils";

const ReactTableFixedColumns = withFixedColumns(ReactTable);

export default class Summary extends React.Component {
  constructor(props) {
    super(props);

    this.state = {
      fixed: true,
    };
    this.infos = [
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
    this.headerWidth = window.innerWidth * 0.15;
    this.width = window.innerWidth;
  }

  renderTooltip = (cell) =>
    Object.keys(cell)
      .filter((key) => cell[key] && key !== "sum")
      .map((key) => `${key}: ${cell[key]}`)
      .join(", ") || undefined;

  //fix columns
  handleInputChange = ({ target }) => {
    this.setState({
      [target.name]: target.checked,
    });
  };

  renderEnvironmentRow = (row, text, colSpan, j) => {
    if (row === "options") {
      return (
        <td
          colSpan={colSpan}
          key={text + j}
          className="header__tool-row options"
        >
          <ul>{this.renderOptions(text)}</ul>
        </td>
      );
    }
    return (
      <td colSpan={colSpan} key={text + j} className="header__tool-row">
        {text}{" "}
      </td>
    );
  };
  renderOptions = (text) => {
    return text.split(/[\s]+-/).map((option, i) => (
      <li key={option}>
        <code>{i === 0 ? option : `-${option}`}</code>
      </li>
    ));
  };

  createRowTitleColumn = () => ({
    Header: () => (
      <div className="toolsHeader">
        <form>
          <label title="Fix the first column">
            Fixed row title:
            <input
              id="fixed-row-title"
              name="fixed"
              type="checkbox"
              checked={this.state.fixed}
              onChange={this.handleInputChange}
            />
          </label>
        </form>
      </div>
    ),
    fixed: this.state.fixed ? "left" : "",
    minWidth: this.headerWidth,
    columns: [
      {
        id: "summary",
        minWidth: this.headerWidth,
        Header: <SelectColumnsButton handler={this.props.selectColumn} />,
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

  createColumn = (runSetIdx, column, columnIdx) => ({
    id: `${runSetIdx}_${column.display_title}_${columnIdx}`,
    Header: (
      <StandardColumnHeader
        column={column}
        className="columns"
        title="Show Quantile Plot of this column"
        onClick={(e) => this.props.changeTab(e, column, 2)}
      />
    ),
    show:
      !this.props.hiddenCols[runSetIdx].includes(columnIdx) &&
      (isNumericColumn(column) || column.type === "status"),
    minWidth: determineColumnWidth(
      column,
      null,
      column.type === "status" ? 6 : null,
    ),
    accessor: (row) => row.content[runSetIdx][columnIdx],
    Cell: (cell) =>
      cell.value ? (
        <div
          dangerouslySetInnerHTML={{ __html: cell.value.sum }}
          className="cell"
          title={this.renderTooltip(cell.value)}
        ></div>
      ) : (
        <div className="cell">-</div>
      ),
  });

  render() {
    const statColumns = this.props.tools
      .map((runSet, runSetIdx) =>
        createRunSetColumns(runSet, runSetIdx, this.createColumn),
      )
      .flat();

    return (
      <div id="summary">
        <div id="benchmark_setup">
          <h2>Benchmark Setup</h2>
          <table>
            <tbody>
              {this.infos
                .map((row) => this.props.tableHeader[row])
                .filter((row) => row !== null)
                .map((row, i) => (
                  <tr key={"tr-" + row.id} className={row.id}>
                    <th key={"td-" + row.id}>{row.name}</th>
                    {row.content.map((tool, j) =>
                      this.renderEnvironmentRow(row.id, tool[0], tool[1], j),
                    )}
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
        <div id="statistics">
          <h2>Statistics</h2>
          <ReactTableFixedColumns
            data={this.props.stats}
            columns={[this.createRowTitleColumn()].concat(statColumns)}
            showPagination={false}
            className="-highlight"
            minRows={0}
            sortable={false}
            width={this.width}
          />
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
            BenchExec {this.props.version}
          </a>
        </p>
      </div>
    );
  }
}
