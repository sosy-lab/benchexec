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
  constructor(props: any) {
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
    // @ts-expect-error TS(2339): Property 'resetFilterHook' does not exist on type ... Remove this comment to see the full error message
    this.props.resetFilterHook(() => this.resetAllFilters());
    this.state = { filters, toolName, addingFilter: false, numCards: 0 };
  }

  getActiveFilters() {
    // @ts-expect-error TS(2339): Property 'filters' does not exist on type 'Readonl... Remove this comment to see the full error message
    return this.state.filters
      .filter((item: any) => item.filtering)
      .sort((a: any, b: any) => a.numCards - b.numCards);
  }

  setFilter({ title, values, filtering = true }: any, idx: any) {
    // @ts-expect-error TS(2339): Property 'filters' does not exist on type 'Readonl... Remove this comment to see the full error message
    const prevFilters = this.state.filters;
    prevFilters[idx].values = values;
    prevFilters[idx].filtering = filtering;
    prevFilters[idx].touched += 1;
    this.setState({ filters: [...prevFilters] });
    // @ts-expect-error TS(2339): Property 'updateFilters' does not exist on type 'R... Remove this comment to see the full error message
    this.props.updateFilters({ title, values }, idx);
  }

  addFilter(idx: any) {
    // @ts-expect-error TS(2339): Property 'filters' does not exist on type 'Readonl... Remove this comment to see the full error message
    const { filters: newFilterState, numCards } = this.state;
    const newFilter = { filtering: true, numCards, touched: 0 };
    if (newFilterState[idx].type === "status") {
      // @ts-expect-error TS(2339): Property 'values' does not exist on type '{ filter... Remove this comment to see the full error message
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
    // @ts-expect-error TS(2339): Property 'filters' does not exist on type 'Readonl... Remove this comment to see the full error message
    const setFilters = this.state.filters.filter((item: any) => item.filtering);
    // @ts-expect-error TS(2339): Property 'filters' does not exist on type 'Readonl... Remove this comment to see the full error message
    const newFilterState = this.state.filters.map((filter: any) => ({
      ...filter,
      filtering: false,
      values: [],
    }));
    this.setState({ filters: [...newFilterState] });
    for (const filter of setFilters) {
      if (filter.values) {
        // @ts-expect-error TS(2339): Property 'updateFilters' does not exist on type 'R... Remove this comment to see the full error message
        this.props.updateFilters(
          { title: filter.display_title, values: [] },
          filter.idx,
        );
      }
    }
  }

  removeFilter(idx: any, title: any) {
    // @ts-expect-error TS(2339): Property 'filters' does not exist on type 'Readonl... Remove this comment to see the full error message
    const newFilterState = this.state.filters;
    newFilterState[idx].filtering = false;
    newFilterState[idx].values = [];
    this.setState({ filters: [...newFilterState] });
    // @ts-expect-error TS(2339): Property 'updateFilters' does not exist on type 'R... Remove this comment to see the full error message
    this.props.updateFilters({ title, values: [] }, idx);
  }

  // @ts-expect-error TS(7031): Binding element 'prevFilters' implicitly has an 'a... Remove this comment to see the full error message
  componentDidUpdate({ currentFilters: prevFilters }) {
    // @ts-expect-error TS(2339): Property 'currentFilters' does not exist on type '... Remove this comment to see the full error message
    const { currentFilters } = this.props;
    if (!equals(prevFilters, currentFilters)) {
      // update set filters
      // @ts-expect-error TS(2339): Property 'filters' does not exist on type 'Readonl... Remove this comment to see the full error message
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
      filters = filters.map((filter: any, idx: any) => {
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
    // @ts-expect-error TS(2339): Property 'hiddenCols' does not exist on type 'Read... Remove this comment to see the full error message
    const hiddenCols = this.props.hiddenCols || [];
    // @ts-expect-error TS(2339): Property 'filters' does not exist on type 'Readonl... Remove this comment to see the full error message
    const availableFilters = this.state.filters.filter(
      (i: any, idx: any) => !i.filtering && !hiddenCols.includes(idx),
    );
    return (
      <div className="filterBox--container">
        // @ts-expect-error TS(2339): Property 'toolName' does not exist on type
        'Readon... Remove this comment to see the full error message
        <h4 className="section-header">{this.state.toolName}</h4>
        {filters.length > 0 &&
          // @ts-expect-error TS(6133): 'idx' is declared but its value is never read.
          filters.map((filter: any, idx: any) => (
            <FilterCard
              // @ts-expect-error TS(2322): Type '{ onFilterUpdate: (val: any) => void; title:... Remove this comment to see the full error message
              onFilterUpdate={(val: any) => this.setFilter(val, filter.idx)}
              title={filter.display_title}
              removeFilter={() =>
                this.removeFilter(filter.idx, filter.display_title)
              }
              filter={filter}
              // @ts-expect-error TS(2339): Property 'toolName' does not exist on type 'Readon... Remove this comment to see the full error message
              key={`${this.props.toolName}-${filter.display_title}-${filter.numCards}`}
            />
          ))}
        {(availableFilters.length && (
          <FilterCard
            // @ts-expect-error TS(2322): Type '{ availableFilters: any; editable: string; s... Remove this comment to see the full error message
            availableFilters={availableFilters}
            editable="true"
            style={{ marginBottom: 20 }}
            addFilter={(idx: any) => this.addFilter(idx)}
            // @ts-expect-error TS(2554): Expected 2 arguments, but got 1.
            onFilterUpdate={(vals: any) => this.setFilter(vals)}
          />
        )) ||
          undefined}
        <br />
      </div>
    );
  }
}
