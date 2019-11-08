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
import "react-table/react-table.css";
import {
  applyFilter,
  sortMethod,
  determineColumnWidth,
  formatColumnTitle,
  maybeTransformToLowercase
} from "../utils/utils";

const ReactTableFixedColumns = withFixedColumns(ReactTable);
export default class Table extends React.Component {
  constructor(props) {
    super(props);

    this.data = this.props.data;
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
    this.typingTimer = -1;
    this.height = window.innerHeight - 50;
  }
  //fix columns
  handleInputChange = ({ target }) => {
    const value = target.checked;
    const name = target.name;

    this.setState({
      [name]: value
    });
  };

  renderColumns = () => {
    return this.props.tools.map((tool, j) => {
      return tool.columns.map((column, i) => {
        //distinguish between column type status (dropdown filter) and other types (input field)
        if (column.type === "status") {
          return {
            id: `${j}_${column.display_title}_${i}`,
            Header: () => (
              <span
                title="Click here to sort. Hold shift to multi-sort"
                className="btn"
              >
                {formatColumnTitle(column)}
              </span>
            ),
            show: column.isVisible,
            minWidth: determineColumnWidth(column, 10),
            accessor: row => row.results[j].values[i],
            Cell: cell => {
              const runResult = cell.original.results[j];
              const value = cell.value;
              return value.raw ? (
                <a
                  href={runResult.href}
                  className={runResult.category}
                  onClick={ev =>
                    this.props.toggleLinkOverlay(ev, runResult.href)
                  }
                  title="Click here to show output of tool"
                  dangerouslySetInnerHTML={
                    value.html ? { __html: value.html } : undefined
                  }
                >
                  {value.html ? undefined : value.raw}
                </a>
              ) : null;
            },
            sortMethod: (a, b, desc) => {
              a = maybeTransformToLowercase(a.raw);
              b = maybeTransformToLowercase(b.raw);
              return a > b ? 1 : a < b ? -1 : 0;
            },
            filterMethod: (filter, row) => {
              //case category has to be differentiated to the name of the status => space in String (e.g. "ERROR ")
              const cleanFilterValue = filter.value.trim().toLowerCase();

              if (cleanFilterValue === "all") {
                return true;
              } else if (
                ["correct", "wrong", "error", "unknown"].includes(
                  cleanFilterValue
                ) &&
                row._original.results[j].category === cleanFilterValue
              ) {
                return row[filter.id];
              } else if (
                row[filter.id] &&
                filter.value === row[filter.id].raw
              ) {
                return row[filter.id];
              }
            },
            Filter: ({ filter, onChange }) => {
              return (
                <select
                  onChange={event => onChange(event.target.value)}
                  style={{ width: "100%" }}
                  value={filter ? filter.value : "all"}
                >
                  <option value="all ">Show all</option>
                  <optgroup label="Category">
                    <option value="correct ">correct</option>
                    <option value="wrong ">wrong</option>
                    <option value="error ">error</option>
                    <option value="unknown ">unknown</option>
                  </optgroup>
                  <optgroup label="Status">{this.collectStati(j, i)}</optgroup>
                </select>
              );
            }
          };
        }
        //other column types with input field filtering
        else {
          return {
            id: `${j}_${column.display_title}_${i}`,
            Header: () => (
              <div title="Click here to sort. Hold shift to multi-sort">
                {formatColumnTitle(column)}
              </div>
            ),
            show: column.isVisible,
            minWidth: determineColumnWidth(column),
            accessor: row => row.results[j].values[i],
            Cell: cell => {
              const html = cell.value.html;
              const raw = html ? undefined : cell.value.raw;
              const href = cell.value.href;
              if (href) {
                return (
                  <a
                    href={href}
                    onClick={ev => this.props.toggleLinkOverlay(ev, href)}
                    dangerouslySetInnerHTML={
                      html ? { __html: html } : undefined
                    }
                  >
                    {raw}
                  </a>
                );
              }
              return (
                <div
                  dangerouslySetInnerHTML={html ? { __html: html } : undefined}
                >
                  {raw}
                </div>
              );
            },
            filterMethod: applyFilter,
            Filter: ({ filter, onChange }) => {
              let value;
              const placeholder =
                column.type === "count" || column.type === "measure"
                  ? "Min:Max"
                  : "text";
              return (
                <input
                  placeholder={placeholder}
                  defaultValue={value ? value : filter ? filter.value : filter}
                  onChange={event => {
                    value = event.target.value;
                    clearTimeout(this.typingTimer);
                    this.typingTimer = setTimeout(() => {
                      onChange(value);
                    }, 500);
                  }}
                />
              );
            },
            sortMethod
          };
        }
      });
    });
  };

  collectStati = (tool, column) => {
    const statiArray = this.data.map(
      row => row.results[tool].values[column].raw
    );
    return [...new Set(statiArray)].map(status =>
      status ? (
        <option value={status} key={status}>
          {status}
        </option>
      ) : null
    );
  };
  renderToolInfo = i => {
    const header = this.props.tableHeader;

    return this.infos.map(row =>
      header[row] ? (
        <p key={row} className="header__tool-row">
          {header[row].content[i][0]}{" "}
        </p>
      ) : null
    );
  };

  render() {
    this.data = this.props.data;
    const toolColumns = this.renderColumns();
    const columns = [
      {
        Header: () => (
          <div className="fixed">
            <form>
              <label title="Fix the first column">Fixed task:</label>
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
        columns: [
          {
            minWidth: window.innerWidth * 0.3,
            Header: () => (
              <div
                onClick={this.props.selectColumn}
                className={"selectColumns"}
              >
                <span>Click here to select columns</span>
              </div>
            ),
            fixed: this.state.fixed ? "left" : "",
            accessor: "id",
            Cell: cell => {
              const content = cell.value.map(id => (
                <span key={id} className="row_id">
                  {id}
                </span>
              ));
              const href = cell.original.href;
              return href ? (
                <a
                  key={href}
                  className="row__name--cellLink"
                  href={href}
                  title="Click here to show source code"
                  onClick={ev => this.props.toggleLinkOverlay(ev, href)}
                >
                  {content}
                </a>
              ) : (
                <span title="This task has no associated file">{content}</span>
              );
            },
            filterMethod: (filter, row, column) => {
              const id = filter.pivotId || filter.id;
              return row[id].some(v => v && v.includes(filter.value));
            }
          }
        ]
      },
      ...toolColumns.map((toolColumn, i) => ({
        id: "results",
        Header: () => (
          <span className="header__tool-infos">
            {this.props.getRunSets(this.props.tools[i])}
          </span>
        ),
        columns: toolColumn
      }))
    ];

    return (
      <div className="mainTable">
        <ReactTableFixedColumns
          data={this.data}
          filterable={true}
          filtered={this.props.filtered}
          columns={columns}
          defaultPageSize={250}
          pageSizeOptions={[50, 100, 250, 500, 1000, 2500]}
          className="-highlight"
          minRows={0}
          onFilteredChange={filtered => {
            this.props.filterPlotData(filtered);
          }}
          style={{ maxHeight: this.height }}
        >
          {(state, makeTable, instance) => {
            this.props.setFilter(state.sortedData);
            return makeTable();
          }}
        </ReactTableFixedColumns>
      </div>
    );
  }
}
