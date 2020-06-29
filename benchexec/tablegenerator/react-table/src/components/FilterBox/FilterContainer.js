// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import React from "react";
import FilterCard from "./FilterCard";
import equals from "deep-equal";

export default class FilterContainer extends React.PureComponent {
  constructor(props) {
    super(props);
    const { filters, toolName } = props;
    this.state = { filters, toolName, addingFilter: false, numCards: 0 };
  }

  getActiveFilters() {
    return this.state.filters
      .filter((item) => item.filtering)
      .sort((a, b) => a.numCards - b.numCards);
  }

  setFilter({ title, values, filtering = true }, idx) {
    console.log("Container received", {
      title,
      values,
      idx,
    });
    const prevFilters = this.state.filters;
    prevFilters[idx].values = values;
    prevFilters[idx].filtering = filtering;
    this.setState({ filters: [...prevFilters] });
    this.props.updateFilters({ title, values }, idx);
  }

  addFilter(idx) {
    const { filters: newFilterState, numCards } = this.state;
    const newFilter = { filtering: true, numCards };
    if (newFilterState[idx].type === "status") {
      newFilter.values = [
        ...newFilterState[idx].categories,
        ...newFilterState[idx].statuses,
      ];
    }
    newFilterState[idx] = { ...newFilterState[idx], ...newFilter };

    this.setState({
      filters: newFilterState,
      addingFilter: false,
      numCards: numCards + 1,
    });
  }

  removeFilter(idx, title) {
    const newFilterState = this.state.filters;
    newFilterState[idx].filtering = false;
    newFilterState[idx].values = [];
    this.setState({ filters: [...newFilterState] });
    this.props.updateFilters({ title, values: [] }, idx);
  }

  componentDidUpdate({ currentFilters: prevFilters }) {
    const { currentFilters } = this.props;
    if (!equals(prevFilters, currentFilters)) {
      // update set filters
      console.log("updated container");
      const { filters } = this.state;
      for (const idx in currentFilters) {
        filters[idx] = {
          ...filters[idx],
          ...currentFilters[idx],
          filtering: true,
        };
      }
      this.setState({ filters: [...filters] });
    }
  }

  render() {
    const filters = this.getActiveFilters();
    console.log("container rendered");
    const availableFilters = this.state.filters.filter((i) => !i.filtering);
    return (
      <div className="filterBox--container">
        <h4>{this.state.toolName}</h4>
        {filters.length === 0
          ? "No Filters set"
          : filters.map((filter, idx) => (
              <FilterCard
                onFilterUpdate={(val) => this.setFilter(val, filter.idx)}
                title={filter.display_title}
                removeFilter={() =>
                  this.removeFilter(filter.idx, filter.display_title)
                }
                filter={filter}
                key={`${this.props.toolName}-${filter.display_title}-${filter.numCards}`}
              />
            ))}
        <br />
        <br />
        {availableFilters.length && (
          <FilterCard
            availableFilters={availableFilters}
            editable="true"
            addFilter={(idx) => this.addFilter(idx)}
            onFilterUpdate={(vals) => this.setFilter(vals)}
          />
        )}
      </div>
    );
  }
}
