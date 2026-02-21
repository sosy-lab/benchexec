// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import React from "react";
import equals from "deep-equal";
import FilterCard from "./FilterCard";

/* ============================================================
 * Domain Types
 * ============================================================
 */

type FilterType = "status" | "text" | "measure" | "number";

/**
 * Describes the externally provided filter state (values/filtering).
 * This is merged into the internal filter definitions on updates.
 */
interface CurrentFilterUpdate {
  values: string[];
  filtering?: boolean;
}

interface FilterDefinition {
  idx: number;
  type: FilterType;
  display_title: string;

  // Only present for status filters.
  categories?: string[];
  statuses?: string[];

  // Runtime state managed by FilterContainer.
  values?: string[];
  filtering?: boolean;
  touched: number;
  numCards: number;

  // Other properties may exist and are forwarded to FilterCard.
  // We keep this open to avoid breaking on additional filter metadata.
  [key: string]: unknown;
}

/* ============================================================
 * Component Types
 * ============================================================
 */

interface FilterUpdatePayload {
  title: string;
  values: string[];
}

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

    // NOTE (JS->TS): Preserve original behavior (mutating the incoming filters array)
    // to keep structure/functionality identical to the JS implementation.
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

  addFilter(idx: number): void {
    const { filters: newFilterState, numCards } = this.state;
    const newFilter: Partial<FilterDefinition> = {
      filtering: true,
      numCards,
      touched: 0,
    };

    if (newFilterState[idx].type === "status") {
      // NOTE (JS->TS): Guard against optional arrays while preserving JS behavior.
      const categories = newFilterState[idx].categories ?? [];
      const statuses = newFilterState[idx].statuses ?? [];
      newFilter.values = [...categories, ...statuses];
    }

    newFilterState[idx] = { ...newFilterState[idx], ...newFilter };

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
            // NOTE (JS->TS): Preserve original prop shape; "editable" was passed as a string in JS.
            editable="true"
            style={{ marginBottom: 20 }}
            addFilter={(idx: number) => this.addFilter(idx)}
            // NOTE (JS->TS): Preserve original call signature; idx is optional here (same as JS behavior).
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
