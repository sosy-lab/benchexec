// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import React from "react";
import FilterContainer from "./FilterContainer";
import TaskFilterCard from "./TaskFilterCard";
import { faTimes, faTrash } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import equals from "deep-equal";
import { isNil } from "../../utils/utils";
const classNames = require("classnames");

export default class FilterBox extends React.PureComponent {
  constructor(props) {
    super(props);

    const { filtered } = props;

    this.listeners = [];

    this.resetFilterHook = (fun) => this.listeners.push(fun);

    this.state = {
      filters: this.createFiltersFromReactTableStructure(filtered),
      idFilters: this.retrieveIdFilters(filtered),
    };
  }

  componentDidUpdate(prevProps) {
    if (!equals(prevProps.filtered, this.props.filtered)) {
      this.setState({
        filters: this.createFiltersFromReactTableStructure(this.props.filtered),
        idFilters: this.retrieveIdFilters(this.props.filtered),
      });
    }
  }

  resetAllFilters() {
    this.resetAllContainers();
    this.resetIdFilters();
  }

  resetIdFilters() {
    const empty = null; //Object.keys(this.props.ids).map(() => null);
    this.setState({ idFilters: empty });
    this.sendFilters({ filter: this.state.filters, idFilter: empty });
  }

  resetAllContainers() {
    this.listeners.forEach((fun) => fun());
  }

  retrieveIdFilters(filters) {
    const possibleIdFilter = filters.find((filter) => filter.id === "id");
    return possibleIdFilter ? possibleIdFilter.values : [];
  }

  createFiltersFromReactTableStructure(filters) {
    if (!filters || !filters.length) {
      return [];
    }

    const out = [];

    for (const { id, value } of filters.flat()) {
      if (id === "id") {
        continue;
      }
      const [tool, title, col] = id.split("_");
      const toolArr = out[tool] || [];
      if (!toolArr[col]) {
        toolArr[col] = { title, values: [value] };
      } else {
        toolArr[col].values.push(value);
      }
      out[tool] = toolArr;
    }
    return out;
  }

  flattenFilterStructure() {
    return Object.values(Object.values(this.state.filters));
  }

  sendFilters({ filter, idFilter }) {
    const newFilter = [
      ...filter
        .map((tool, toolIdx) => {
          if (tool === null || tool === undefined) {
            return null;
          }
          return tool.map((col, colIdx) => {
            return col.values.map((val) => ({
              id: `${toolIdx}_${col.title}_${colIdx}`,
              value: val,
            }));
          });
        })
        .flat(3)
        .filter((i) => i !== null && i !== undefined),
    ];
    newFilter.push({ id: "id", values: idFilter });
    this.props.addTypeToFilter(newFilter);
    this.props.setFilter(newFilter, true);
  }

  updateFilters(toolIdx, columnIdx, data) {
    //this.props.setFilter(newFilter);
    const newFilters = [...this.state.filters];
    const idFilter = this.state.idFilters;
    newFilters[toolIdx] = newFilters[toolIdx] || [];
    newFilters[toolIdx][columnIdx] = data;
    this.setState({ filters: newFilters });
    this.sendFilters({ filter: newFilters, idFilter });
  }

  updateIdFilters(data) {
    const mapped = Object.keys(this.props.ids).map((i) => data[i]);

    const newFilter = mapped.some((item) => item !== "" && !isNil(item))
      ? mapped
      : undefined;

    this.setState({ idFilters: newFilter });

    this.sendFilters({ filter: this.state.filters, idFilter: newFilter });
  }

  render() {
    const hiddenCols = this.props.hiddenCols || [];
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
            onClick={() => this.resetAllFilters()}
          />
        </div>

        <div className="filter-card--container">
          <TaskFilterCard
            ids={this.props.ids}
            updateFilters={(data) => this.updateIdFilters(data)}
            resetFilterHook={this.resetFilterHook}
            filters={this.state.idFilters}
          />
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
                hiddenCols={hiddenCols[idx]}
                key={`filtercontainer-${idx}`}
              />
            );
          })}
        </div>
      </div>
    );
  }
}
