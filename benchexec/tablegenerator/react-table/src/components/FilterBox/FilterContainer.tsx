// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import React, { useState, useEffect, useCallback } from "react";
import FilterCard from "./FilterCard";
import equals from "deep-equal";

interface FilterContainerProps {
  filters: any[];
  toolName: string;
  currentFilters: any[];
  resetFilterHook: (fun: () => void) => void;
  updateFilters: (data: any, idx?: number) => void;
  hiddenCols?: number[];
}

const FilterContainer: React.FC<FilterContainerProps> = ({
                                                           filters: initialFilters,
                                                           toolName,
                                                           currentFilters,
                                                           resetFilterHook,
                                                           updateFilters,
                                                           hiddenCols = [],
                                                         }) => {
  // Initialize filters state by merging currentFilters into initialFilters
  const [filters, setFilters] = useState(() => {
    const mergedFilters = [...initialFilters];
    for (const idx in currentFilters) {
      mergedFilters[idx] = {
        ...mergedFilters[idx],
        ...currentFilters[idx],
        touched: (mergedFilters[idx]?.touched || 0) + 1,
        filtering: true,
      };
    }
    return mergedFilters;
  });

  const [addingFilter, setAddingFilter] = useState(false);
  const [numCards, setNumCards] = useState(0);

  // Register reset hook once
  React.useEffect(() => {
    resetFilterHook(() => resetAllFilters());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const getActiveFilters = useCallback(() => {
    return filters
      .filter((item) => item.filtering)
      .sort((a, b) => a.numCards - b.numCards);
  }, [filters]);

  const setFilter = useCallback(
    ({ title, values, filtering = true }: { title: string; values: any[]; filtering?: boolean }, idx: number) => {
      const prevFilters = [...filters];
      prevFilters[idx] = {
        ...prevFilters[idx],
        values,
        filtering,
        touched: (prevFilters[idx]?.touched || 0) + 1,
      };
      setFilters(prevFilters);
      updateFilters({ title, values }, idx);
    },
    [filters, updateFilters]
  );

  const addFilter = useCallback(
    (idx: number) => {
      const newFilterState = [...filters];
      const newFilter: any = { filtering: true, numCards, touched: 0 };
      if (newFilterState[idx]?.type === "status") {
        newFilter.values = [
          ...(newFilterState[idx]?.categories || []),
          ...(newFilterState[idx]?.statuses || []),
        ];
      }
      newFilterState[idx] = { ...newFilterState[idx], ...newFilter };
      setFilters(newFilterState);
      setAddingFilter(false);
      setNumCards(numCards + 1);
    },
    [filters, numCards]
  );

  const resetAllFilters = useCallback(() => {
    const setFiltersArr = filters.filter((item) => item.filtering);
    const newFilterState = filters.map((filter) => ({
      ...filter,
      filtering: false,
      values: [],
    }));
    setFilters(newFilterState);
    for (const filter of setFiltersArr) {
      if (filter.values) {
        updateFilters({ title: filter.display_title, values: [] }, filter.idx);
      }
    }
  }, [filters, updateFilters]);

  const removeFilter = useCallback(
    (idx: number, title: string) => {
      const newFilterState = [...filters];
      newFilterState[idx] = {
        ...newFilterState[idx],
        filtering: false,
        values: [],
      };
      setFilters(newFilterState);
      updateFilters({ title, values: [] }, idx);
    },
    [filters, updateFilters]
  );

  useEffect(() => {
    if (!equals(currentFilters, filters.map((f) => ({ ...f, filtering: undefined, touched: undefined })))) {
      let updatedFilters = [...filters];
      for (const idx in currentFilters) {
        updatedFilters[idx] = {
          ...updatedFilters[idx],
          ...currentFilters[idx],
          touched: (updatedFilters[idx]?.touched || 0) + 1,
          filtering: true,
        };
      }
      updatedFilters = updatedFilters.map((filter, idx) => {
        const toBeRemoved = !!(currentFilters[idx] || filter.touched === 0);
        return {
          ...filter,
          filtering: toBeRemoved,
          values: toBeRemoved ? filter.values : [],
        };
      });
      setFilters(updatedFilters);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentFilters]);

  const activeFilters = getActiveFilters();
  const availableFilters = filters.filter(
    (i, idx) => !i.filtering && !hiddenCols.includes(idx)
  );

  return (
    <div className="filterBox--container">
      <h4 className="section-header">{toolName}</h4>
      {activeFilters.length > 0 &&
        activeFilters.map((filter) => (
          <FilterCard
            onFilterUpdate={(val: any) => setFilter(val, filter.idx)}
            title={filter.display_title}
            removeFilter={() => removeFilter(filter.idx, filter.display_title)}
            filter={filter}
            key={`${toolName}-${filter.display_title}-${filter.numCards}`}
          />
        ))}
      {(availableFilters.length > 0 && (
        <FilterCard
          availableFilters={availableFilters}
          editable="true"
          style={{ marginBottom: 20 }}
          addFilter={addFilter}
          onFilterUpdate={(vals: any) => setFilter(vals, -1)}
        />
      )) || undefined}
      <br />
    </div>
  );
};

export default FilterContainer;