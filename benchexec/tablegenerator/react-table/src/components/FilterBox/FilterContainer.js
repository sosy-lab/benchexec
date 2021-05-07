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
    const { filters, toolName, currentFilters } = props;
    for (const idx in currentFilters) {
      filters[idx] = {
        ...filters[idx],
        ...currentFilters[idx],
        touched: filters[idx].touched + 1,
        filtering: true,
      };
    }
    this.props.resetFilterHook(() => this.resetAllFilters());
    this.state = { filters, toolName, addingFilter: false, numCards: 0 };
  }

  getActiveFilters() {
    return this.state.filters
      .filter((item) => item.filtering)
      .sort((a, b) => a.numCards - b.numCards);
  }

  setFilter({ title, values, filtering = true }, idx) {
    const prevFilters = this.state.filters;
    prevFilters[idx].values = values;
    prevFilters[idx].filtering = filtering;
    prevFilters[idx].touched += 1;
    this.setState({ filters: [...prevFilters] });
    this.props.updateFilters({ title, values }, idx);
  }

  addFilter(idx) {
    const { filters: newFilterState, numCards } = this.state;
    const newFilter = { filtering: true, numCards, touched: 0 };
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

  resetAllFilters() {
    const setFilters = this.state.filters.filter((item) => item.filtering);
    const newFilterState = this.state.filters.map((filter) => ({
      ...filter,
      filtering: false,
      values: [],
    }));
    this.setState({ filters: [...newFilterState] });
    for (const filter of setFilters) {
      if (filter.values) {
        this.props.updateFilters(
          { title: filter.display_title, values: [] },
          filter.idx,
        );
      }
    }
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
      let { filters } = this.state;
      for (const idx in currentFilters) {
        filters[idx] = {
          ...filters[idx],
          ...currentFilters[idx],
          touched: filters[idx].touched + 1,
          filtering: true,
        };
      }
      // remove all filters that are not currently filtered
      filters = filters.map((filter, idx) => {
        const toBeRemoved = !!(currentFilters[idx] || filter.touched === 0);
        return {
          ...filter,
          filtering: toBeRemoved,
          values: toBeRemoved ? filter.values : [],
        };
      });
      this.setState({ filters: [...filters] });
    }
  }

  render() {
    const filters = this.getActiveFilters();
    const hiddenCols = this.props.hiddenCols || [];
    const availableFilters = this.state.filters.filter(
      (i, idx) => !i.filtering && !hiddenCols.includes(idx),
    );
    return (
      <div className="filterBox--container">
        <h4 className="section-header">{this.state.toolName}</h4>
        {filters.length > 0 &&
          filters.map((filter, idx) => (
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
        {(availableFilters.length && (
          <FilterCard
            availableFilters={availableFilters}
            editable="true"
            style={{ marginBottom: 20 }}
            addFilter={(idx) => this.addFilter(idx)}
            onFilterUpdate={(vals) => this.setFilter(vals)}
          />
        )) ||
          undefined}
        <br />
      </div>
    );
  }
}
