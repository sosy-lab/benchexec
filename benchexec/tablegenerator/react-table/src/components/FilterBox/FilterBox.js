// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import React from "react";
import FilterContainer from "./FilterContainer";
import { faTimes, faTrash } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import equals from "deep-equal";
const classNames = require("classnames");

export default class FilterBox extends React.PureComponent {
  constructor(props) {
    super(props);

    const { filtered } = props;

    this.listeners = [];

    this.resetFilterHook = (fun) => this.listeners.push(fun);

    this.state = {
      filters: this.createFiltersFromReactTableStructure(filtered),
    };
  }

  componentDidUpdate(prevProps) {
    if (!equals(prevProps.filtered, this.props.filtered)) {
      this.setState({
        filters: this.createFiltersFromReactTableStructure(this.props.filtered),
      });
    }
  }

  resetAllContainers() {
    this.listeners.forEach((fun) => fun());
  }

  createFiltersFromReactTableStructure(filters) {
    const start = Date.now();
    if (!filters || !filters.length) {
      return [];
    }

    const out = [];

    for (const { id, value } of filters.flat()) {
      const [tool, title, col] = id.split("_");
      const toolArr = out[tool] || [];
      if (!toolArr[col]) {
        toolArr[col] = { title, values: [value] };
      } else {
        toolArr[col].values.push(value);
      }
      out[tool] = toolArr;
    }
    console.log(`creation of filter structure took ${Date.now() - start} ms`);
    return out;
  }

  flattenFilterStructure() {
    return Object.values(Object.values(this.state.filters));
  }

  sendFilters(filter) {
    const filters = filter.filter((i) => i !== null && i !== undefined);

    this.props.setFilter(
      filters
        .map((tool, toolIdx) => {
          return tool.map((col, colIdx) => {
            return col.values.map((val) => ({
              id: `${toolIdx}_${col.title}_${colIdx}`,
              value: val,
            }));
          });
        })
        .flat(3)
        .filter((i) => i !== null && i !== undefined),
      true,
    );
  }

  updateFilters(toolIdx, columnIdx, data) {
    //this.props.setFilter(newFilter);
    const newFilters = [...this.state.filters];
    newFilters[toolIdx] = newFilters[toolIdx] || [];
    newFilters[toolIdx][columnIdx] = data;
    this.setState({ filters: newFilters });
    this.sendFilters(newFilters);
  }

  render() {
    return (
      <div
        className={classNames("filterBox", {
          "filterBox--hidden": !this.props.visible,
        })}
      >
        <div className="filterBox--header">
          <FontAwesomeIcon
            icon={faTimes}
            className="filterBox--header--icon"
            onClick={this.props.hide}
          />
          {this.props.headerComponent}
          <FontAwesomeIcon
            icon={faTrash}
            className="filterBox--header--reset-icon"
            onClick={() => this.resetAllContainers()}
          />
        </div>
        {this.props.filterable.map((tool, idx) => {
          return (
            <FilterContainer
              resetFilterHook={this.resetFilterHook}
              updateFilters={(data, columnIndex) =>
                this.updateFilters(idx, columnIndex, data)
              }
              currentFilters={this.state.filters[idx] || []}
              toolName={tool.name}
              filters={tool.columns}
              key={`filtercontainer-${idx}`}
            />
          );
        })}
      </div>
    );
  }
}
