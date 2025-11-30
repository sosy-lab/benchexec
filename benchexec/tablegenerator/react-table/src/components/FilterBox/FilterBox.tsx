// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import React, { useState, useEffect, useRef, useCallback } from "react";
import FilterContainer from "./FilterContainer";
import TaskFilterCard from "./TaskFilterCard";
import { faClose, faTrash } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import equals from "deep-equal";
import { decodeFilter, isNil } from "../../utils/utils";
const classNames = require("classnames");

interface FilterBoxProps {
  filtered: any[];
  ids: Record<string, any>;
  filterable: {
    name: string;
    columns: any[];
  }[];
  hiddenCols?: any[][];
  visible: boolean;
  headerComponent?: React.ReactNode;
  hide: () => void;
  addTypeToFilter: (filter: any[]) => void;
  setFilter: (filter: any[], flag: boolean) => void;
}

const FilterBox: React.FC<FilterBoxProps> = (props) => {
  const { filtered, ids, filterable, hiddenCols = [], visible, headerComponent, hide, addTypeToFilter, setFilter } = props;

  const listeners = useRef<(() => void)[]>([]);

  const resetFilterHook = useCallback((fun: () => void) => {
    listeners.current.push(fun);
  }, []);

  const createFiltersFromReactTableStructure = useCallback((filters: any[]) => {
    if (!filters || !filters.length) {
      return [];
    }

    const out: any[] = [];

    for (const { id, value } of filters.flat()) {
      if (id === "id") {
        continue;
      }
      const { tool, name: title, column } = decodeFilter(id) as { tool: number; name: string; column: number };
      const toolArr = out[tool] || [];
      if (!toolArr[column]) {
        toolArr[column] = { title, values: [value] };
      } else {
        toolArr[column].values.push(value);
      }
      out[tool] = toolArr;
    }
    return out;
  }, []);

  const retrieveIdFilters = useCallback((filters: any[]) => {
    const possibleIdFilter = filters.find((filter) => filter.id === "id");
    return possibleIdFilter ? possibleIdFilter.values : [];
  }, []);

  const [filters, setFilters] = useState(() => createFiltersFromReactTableStructure(filtered));
  const [idFilters, setIdFilters] = useState(() => retrieveIdFilters(filtered));

  useEffect(() => {
    if (!equals(filtered, filters)) {
      setFilters(createFiltersFromReactTableStructure(filtered));
      setIdFilters(retrieveIdFilters(filtered));
    }
  }, [filtered, createFiltersFromReactTableStructure, retrieveIdFilters]);

  const resetAllContainers = useCallback(() => {
    listeners.current.forEach((fun) => fun());
  }, []);

  const resetIdFilters = useCallback(() => {
    const empty = null;
    setIdFilters(empty);
    sendFilters({ filter: filters, idFilter: empty });
  }, [filters]);

  const resetAllFilters = useCallback(() => {
    resetAllContainers();
    resetIdFilters();
  }, [resetAllContainers, resetIdFilters]);

  const sendFilters = useCallback(
    ({ filter, idFilter }: { filter: any[]; idFilter: any }) => {
      const newFilter = [
        ...filter
          .map((tool, toolIdx) => {
            if (tool === null || tool === undefined) {
              return null;
            }
            return tool.map((col: any, colIdx: number) => {
              return col.values.map((val: any) => ({
                id: `${toolIdx}_${col.title}_${colIdx}`,
                value: val,
              }));
            });
          })
          .flat(3)
          .filter((i) => i !== null && i !== undefined),
      ];
      if (idFilter && idFilter.length > 0) {
        newFilter.push({ id: "id", values: idFilter });
      }

      addTypeToFilter(newFilter);
      setFilter(newFilter, true);
    },
    [addTypeToFilter, setFilter]
  );

  const updateFilters = useCallback(
    (toolIdx: number, columnIdx: number, data: any) => {
      const newFilters = [...filters];
      const idFilter = idFilters;
      newFilters[toolIdx] = newFilters[toolIdx] || [];
      newFilters[toolIdx][columnIdx] = data;
      setFilters(newFilters);
      sendFilters({ filter: newFilters, idFilter });
    },
    [filters, idFilters, sendFilters]
  );

  const updateIdFilters = useCallback(
    (data: any) => {
      const mapped = Object.keys(ids).map((i) => data[i]);

      const newFilter = mapped.some((item) => item !== "" && !isNil(item)) ? mapped : undefined;

      setIdFilters(newFilter);

      sendFilters({ filter: filters, idFilter: newFilter });
    },
    [ids, filters, sendFilters]
  );

  return (
    <div
      className={classNames("filterBox", {
        "filterBox--hidden": !visible,
      })}
    >
      <div className="filterBox--header">
        <FontAwesomeIcon icon={faClose} className="filterBox--header--icon" onClick={hide} />
        {headerComponent}
        <FontAwesomeIcon icon={faTrash} className="filterBox--header--reset-icon" onClick={resetAllFilters} />
      </div>

      <div className="filter-card--container">
        <TaskFilterCard ids={ids} updateFilters={updateIdFilters} resetFilterHook={resetFilterHook} filters={idFilters} />
        {filterable.map((tool, idx) => (
          <FilterContainer
            resetFilterHook={resetFilterHook}
            updateFilters={(data: any, columnIndex: any) => updateFilters(idx, columnIndex, data)}
            currentFilters={filters[idx] || []}
            toolName={tool.name}
            filters={tool.columns}
            hiddenCols={hiddenCols[idx]}
            key={`filtercontainer-${idx}`}
          />
        ))}
      </div>
    </div>
  );
};

export default FilterBox;