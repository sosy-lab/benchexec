/* SPDX-License-Identifier: Apache-2.0
 *
 * BenchExec is a framework for reliable benchmarking.
 * This file is part of BenchExec.
 * Copyright (C) Dirk Beyer. All rights reserved.
 */
import React from "react";
import ReactTable from "react-table";
import "react-table/react-table.css";
import withFixedColumns from "react-table-hoc-fixed-columns";
import "react-table-hoc-fixed-columns/lib/styles.css";

const ReactTableFixedColumns = withFixedColumns(ReactTable);

export default class Summary extends React.Component {
  constructor(props) {
    super(props);

    this.state = {
      fixed: true
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
      "property"
    ];
    this.headerWidth = window.innerWidth * 0.15;
    this.width = window.innerWidth;
  }

  renderResultTable = () => {
    return this.props.tools.map((tool, j) => {
      return tool.columns.map((column, i) => {
        return {
          id: `${j}_${column.display_title}_${i}`,
          Header: () => (
            <div
              className="columns"
              title="Show Quantile Plot of this column"
              onClick={e => this.props.changeTab(e, column, 2)}
            >
              {column.display_title}
              {column.unit ? ` (${column.unit})` : ""}
            </div>
          ),
          show: column.isVisible,
          accessor: props =>
            props.content[j][i] ? (
              <div
                dangerouslySetInnerHTML={{ __html: props.content[j][i].sum }}
                className="summary_span"
                title={this.renderTooltip(props.content[j][i])}
              ></div>
            ) : (
              <div className="summary_span">-</div>
            )
        };
      });
    });
  };

  renderTooltip = cell =>
    Object.keys(cell)
      .filter(key => cell[key] && key !== "sum")
      .map(key => `${key}: ${cell[key]}`)
      .join(", ") || undefined;

  //fix columns
  handleInputChange = ({ target }) => {
    this.setState({
      [target.name]: target.checked
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
  renderOptions = text => {
    return text.split(/[\s]+-/).map((option, i) => (
      <li key={option}>
        <code>{i === 0 ? option : `-${option}`}</code>
      </li>
    ));
  };

  render() {
    const toolColumns = this.renderResultTable();
    //preperation of columns for a ReactTable
    const column = [
      {
        Header: () => (
          <div className="toolsHeader">
            <form>
              <label>Fixed row title:</label>
              <input
                name="fixed"
                type="checkbox"
                checked={this.state.fixed}
                onChange={this.handleInputChange}
              />
            </form>
          </div>
        ),
        fixed: this.state.fixed ? "left" : "",
        width: this.headerWidth,
        columns: [
          {
            id: "summary",
            width: this.headerWidth,
            Header: () => (
              <div onClick={this.props.selectColumn}>
                <span>Click here to select columns</span>
              </div>
            ),
            accessor: props => (
              <div
                dangerouslySetInnerHTML={{ __html: props.title }}
                title={props.description}
                className="tr"
              />
            )
          }
        ]
      },
      ...toolColumns.map((toolColumn, i) => {
        return {
          id: "results",
          Header: () => (
            <div className="header__tool-infos">
              {this.props.getRunSets(this.props.tools[i], i)}
            </div>
          ),
          columns: toolColumn
        };
      })
    ];

    return (
      <div id="summary">
        <div id="benchmark_setup">
          <h2>Benchmark Setup</h2>
          <table>
            <tbody>
              {this.infos
                .map(row => this.props.tableHeader[row])
                .filter(row => row !== null)
                .map((row, i) => (
                  <tr key={"tr-" + row.id} className={row.id}>
                    <th key={"td-" + row.id}>{row.name}</th>
                    {row.content.map((tool, j) =>
                      this.renderEnvironmentRow(row.id, tool[0], tool[1], j)
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
            columns={column}
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
            BenchExec {window.data.version}
          </a>
        </p>
      </div>
    );
  }
}
