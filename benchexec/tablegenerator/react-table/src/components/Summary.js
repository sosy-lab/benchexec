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

  renderTooltip = cell => {
    return Object.keys(cell)
      .filter(key => cell[key] && key !== "sum")
      .map(key => `${key}: ${cell[key]}`)
      .join(", ");
  };

  //fix columns
  handleInputChange = ({ target }) => {
    this.setState({
      [target.name]: target.checked
    });
  };
  renderOptions = text => {
    return text.split("-").map(option => (
      <li key={option}>
        <code>{`-${option}`}</code>
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
              <label>Fixed:</label>
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
      <div className="summary">
        <h2>Environment</h2>
        <table>
          <tbody>
            {this.infos
              .filter(info => this.props.tableHeader[info] !== null)
              .map((row, i) => (
                <tr key={"tr-" + row}>
                  <th key={"td-" + row}>{row}</th>
                  {this.props.tableHeader[row].content.map((tool, j) =>
                    row !== "options" ? (
                      <td
                        colSpan={tool[1]}
                        key={tool[0] + j}
                        className="header__tool-row"
                      >
                        {tool[0]}{" "}
                      </td>
                    ) : (
                      <td
                        colSpan={tool[1]}
                        key={tool[0] + j}
                        className="header__tool-row options"
                      >
                        <ul>{this.renderOptions(tool[0])}</ul>
                      </td>
                    )
                  )}
                </tr>
              ))}
          </tbody>
        </table>
        <h2>Summary</h2>
        <ReactTableFixedColumns
          data={this.props.stats}
          columns={column}
          showPagination={false}
          className="-highlight"
          minRows={0}
          sortable={false}
          width={this.width}
        />
        <p>
          Generated by{" "}
          <a
            className="link"
            href="https://github.com/sosy-lab/benchexec"
            target="_blank"
            rel="noopener noreferrer"
          >
            {" "}
            BenchExec
          </a>
        </p>
      </div>
    );
  }
}
