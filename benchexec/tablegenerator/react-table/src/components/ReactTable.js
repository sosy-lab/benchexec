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
  getRawOrDefault,
  isNumericColumn,
  applyNumericFilter,
  applyTextFilter,
  numericSortMethod,
  textSortMethod,
  determineColumnWidth,
  formatColumnTitle
} from "../utils/utils";

class FilterInputField extends React.Component {
  constructor(props) {
    super(props);
    this.elementId = props.column.id + "_filter";
    this.filter = props.filter ? props.filter.value : props.filter;
  }

  numericPattern = "([+-]?[0-9]*(\\.[0-9]*)?)(:[+-]?[0-9]*(\\.[0-9]*)?)?";

  onChange = event => {
    this.value = event.target.value;
    clearTimeout(this.typingTimer);
    this.typingTimer = setTimeout(() => {
      this.props.onChange(this.value);
      document.getElementById(this.elementId).focus();
    }, 500);
  };

  render = () => (
    <input
      id={this.elementId}
      placeholder={this.props.numeric ? "Min:Max" : "text"}
      defaultValue={this.value ? this.value : this.filter}
      onChange={this.onChange}
      type="search"
      pattern={this.props.numeric ? this.numericPattern : undefined}
    />
  );
}

const ReactTableFixedColumns = withFixedColumns(ReactTable);
export default class Table extends React.Component {
  constructor(props) {
    super(props);

    this.data = this.props.data;
    this.state = {
      fixed: true,
      height: window.innerHeight - 50
    };

    // Collect all status and category values for filter drop-down
    this.statusValues = this.findAllValuesOfColumn(
      (tool, column) => column.type === "status",
      (runResult, value) => getRawOrDefault(value)
    );
    this.categoryValues = this.findAllValuesOfColumn(
      (tool, column) => column.type === "status",
      (runResult, value) =>
        getRawOrDefault(value) ? runResult.category : undefined
    );

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
            sortMethod: textSortMethod,
            filterMethod: (filter, row) => {
              const cellValue = getRawOrDefault(row[filter.id]);
              if (!filter.value || filter.value === "all ") {
                return true;
              } else if (cellValue === undefined) {
                return false; // empty cells never match
              } else if (filter.value.endsWith(" ")) {
                // category filters are marked with space at end
                const category = row._original.results[j].category;
                return category === filter.value.trim();
              } else {
                return filter.value === cellValue;
              }
            },
            Filter: ({ filter, onChange }) => {
              return (
                <select
                  onChange={event => onChange(event.target.value)}
                  style={{ width: "100%" }}
                  value={filter ? filter.value : "all "}
                >
                  <option value="all ">Show all</option>
                  <optgroup label="Category">
                    {this.categoryValues[j][i].map(category => (
                      // category filters are marked with space at end
                      <option value={category + " "} key={category}>
                        {category}
                      </option>
                    ))}
                  </optgroup>
                  <optgroup label="Status">
                    {this.statusValues[j][i].map(status => (
                      <option value={status} key={status}>
                        {status}
                      </option>
                    ))}
                  </optgroup>
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
            filterMethod: isNumericColumn(column)
              ? applyNumericFilter
              : applyTextFilter,
            Filter: filter => (
              <FilterInputField numeric={isNumericColumn(column)} {...filter} />
            ),
            sortMethod: isNumericColumn(column)
              ? numericSortMethod
              : textSortMethod
          };
        }
      });
    });
  };

  findAllValuesOfColumn = (columnFilter, valueAccessor) =>
    this.props.tools.map((tool, j) =>
      tool.columns.map((column, i) => {
        if (!columnFilter(tool, column)) {
          return undefined;
        }
        const values = this.data
          .map(row => valueAccessor(row.results[j], row.results[j].values[i]))
          .filter(Boolean);
        return [...new Set(values)].sort();
      })
    );

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
            },
            Filter: FilterInputField
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
          style={{ maxHeight: "calc(100% - 50px)" }}
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
