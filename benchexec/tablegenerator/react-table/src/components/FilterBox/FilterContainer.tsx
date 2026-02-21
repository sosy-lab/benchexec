// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import React from "react";
import equals from "deep-equal";
import FilterCard from "./FilterCard";
import {
  CurrentFilterUpdate,
  FilterUpdatePayload,
  FilterDefinition,
} from "./types";

interface FilterContainerProps {
  filters: FilterDefinition[];
  toolName: string;
  currentFilters: Record<number, CurrentFilterUpdate>;
  hiddenCols?: number[];

  updateFilters: (payload: FilterUpdatePayload, idx: number) => void;
  resetFilterHook: (fn: () => void) => void;
}

interface FilterContainerState {
  filters: FilterDefinition[];
  toolName: string;
  addingFilter: boolean;
  numCards: number;
}

export default class FilterContainer extends React.PureComponent<
  FilterContainerProps,
  FilterContainerState
> {
  constructor(props: FilterContainerProps) {
    super(props);
    const { filters, toolName, currentFilters } = props;
    for (const idxStr in currentFilters) {
      const idx = Number(idxStr);
      filters[idx] = {
        ...filters[idx],
        ...currentFilters[idx],
        touched: (filters[idx]?.touched ?? 0) + 1,
        filtering: true,
      };
    }

    this.props.resetFilterHook(() => this.resetAllFilters());
    this.state = { filters, toolName, addingFilter: false, numCards: 0 };
  }

  getActiveFilters(): FilterDefinition[] {
    return this.state.filters
      .filter((item) => Boolean(item.filtering))
      .sort((a, b) => a.numCards - b.numCards);
  }

  setFilter(
    {
      title,
      values,
      filtering = true,
    }: FilterUpdatePayload & { filtering?: boolean },
    idx: number,
  ): void {
    const prevFilters = this.state.filters;
    prevFilters[idx].values = values;
    prevFilters[idx].filtering = filtering;
    prevFilters[idx].touched += 1;
    this.setState({ filters: [...prevFilters] });
    this.props.updateFilters({ title, values }, idx);
  }

  // NOTE (JS->TS): avoids mutating React state in-place, preserves the discriminated-union type narrowing
  // by branching on filter.type, and builds a well-typed next FilterDefinition (including status default values)
  // so TypeScript can verify correctness and React updates stay predictable.
  addFilter(idx: number): void {
    const { numCards } = this.state;
    const newFilterState = [...this.state.filters];
    const prev = newFilterState[idx];

    const commonUpdate = {
      filtering: true,
      numCards,
      touched: 0,
    };

    if (prev.type === "status") {
      const categories = prev.categories ?? [];
      const statuses = prev.statuses ?? [];
      newFilterState[idx] = {
        ...prev,
        ...commonUpdate,
        values: [...categories, ...statuses],
      };
    } else {
      newFilterState[idx] = {
        ...prev,
        ...commonUpdate,
      };
    }

    this.setState({
      filters: newFilterState,
      addingFilter: false,
      numCards: numCards + 1,
    });
  }

  resetAllFilters(): void {
    const setFilters = this.state.filters.filter((item) =>
      Boolean(item.filtering),
    );
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

  removeFilter(idx: number, title: string): void {
    const newFilterState = this.state.filters;
    newFilterState[idx].filtering = false;
    newFilterState[idx].values = [];
    this.setState({ filters: [...newFilterState] });
    this.props.updateFilters({ title, values: [] }, idx);
  }

  componentDidUpdate(prevProps: FilterContainerProps): void {
    const { currentFilters } = this.props;
    if (!equals(prevProps.currentFilters, currentFilters)) {
      // update set filters
      let { filters } = this.state;
      for (const idxStr in currentFilters) {
        const idx = Number(idxStr);
        filters[idx] = {
          ...filters[idx],
          ...currentFilters[idx],
          touched: (filters[idx]?.touched ?? 0) + 1,
          filtering: true,
        };
      }
      // remove all filters that are not currently filtered
      filters = filters.map((filter, idx) => {
        const toBeRemoved = Boolean(
          currentFilters[idx] || filter.touched === 0,
        );
        return {
          ...filter,
          filtering: toBeRemoved,
          values: toBeRemoved ? filter.values : [],
        };
      });
      this.setState({ filters: [...filters] });
    }
  }

  render(): React.ReactNode {
    const filters = this.getActiveFilters();
    const hiddenCols = this.props.hiddenCols ?? [];
    const availableFilters = this.state.filters.filter(
      (i, idx) => !i.filtering && !hiddenCols.includes(idx),
    );

    return (
      <div className="filterBox--container">
        <h4 className="section-header">{this.state.toolName}</h4>
        {filters.length > 0 &&
          filters.map((filter) => (
            <FilterCard
              onFilterUpdate={(val: FilterUpdatePayload) =>
                this.setFilter(val, filter.idx)
              }
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
            editable={true}
            style={{ marginBottom: 20 }}
            addFilter={(idx: number) => this.addFilter(idx)}
            onFilterUpdate={(vals: FilterUpdatePayload) =>
              this.setFilter(vals, 0)
            }
          />
        )) ||
          undefined}
        <br />
      </div>
    );
  }
}
