// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import React from "react";
import FilterContainer from "./FilterContainer";
import TaskFilterCard from "./TaskFilterCard";
import { faClose, faTrash } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import equals from "deep-equal";
import { decodeFilter, isNil } from "../../utils/utils";
import classNames from "classnames";

/* ---------------------------------------------------------
 * TYPES
 * --------------------------------------------------------- */

export interface ReactTableFilter {
  id: string;
  value?: string;
  values?: string[];
}

export interface FilterableColumn {
  name: string;
  columns: { title: string; column: number }[];
}

interface FilterBoxProps {
  filtered: ReactTableFilter[];
  filterable: FilterableColumn[];
  ids: Record<string, any>;
  hiddenCols?: boolean[][];
  visible: boolean;
  headerComponent?: React.ReactNode;

  hide: () => void;
  addTypeToFilter: (filter: any[]) => void;
  setFilter: (filter: any[], update: boolean) => void;
}

interface SingleColumnFilter {
  title: string;
  values: any[];
}

type ToolFilter = Array<SingleColumnFilter | undefined>;

interface FilterBoxState {
  filters: ToolFilter[];
  idFilters: any[] | null | undefined;
}

/* ---------------------------------------------------------
 * COMPONENT
 * --------------------------------------------------------- */

export default class FilterBox extends React.PureComponent<
  FilterBoxProps,
  FilterBoxState
> {
  private listeners: Array<() => void>;

  constructor(props: FilterBoxProps) {
    super(props);

    const { filtered } = props;

    this.listeners = [];
    this.resetFilterHook = (fun) => this.listeners.push(fun);

    this.state = {
      filters: this.createFiltersFromReactTableStructure(filtered),
      idFilters: this.retrieveIdFilters(filtered),
    };
  }

  /* ---------------------------------------------------------
   * RESET BEHAVIOR
   * --------------------------------------------------------- */

  resetFilterHook: (fun: () => void) => void;

  componentDidUpdate(prevProps: FilterBoxProps) {
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

  resetAllContainers() {
    this.listeners.forEach((fun) => fun());
  }

  resetIdFilters() {
    const empty = null;
    this.setState({ idFilters: empty });
    this.sendFilters({ filter: this.state.filters, idFilter: empty });
  }

  /* ---------------------------------------------------------
   * FILTER PARSING
   * --------------------------------------------------------- */

  retrieveIdFilters(filters: ReactTableFilter[]) {
    const possibleIdFilter = filters.find((f) => f.id === "id");
    return possibleIdFilter ? possibleIdFilter.values : [];
  }

  createFiltersFromReactTableStructure(filters: ReactTableFilter[]) {
    if (!filters || !filters.length) {
      return [];
    }

    const out: ToolFilter[] = [];

    for (const { id, value } of filters.flat()) {
      if (id === "id") continue;

      const { tool, name: title, column } = decodeFilter(id);
      const toolArr = out[tool] || [];

      if (!toolArr[column]) {
        toolArr[column] = { title, values: [value] };
      } else {
        toolArr[column]!.values.push(value);
      }

      out[tool] = toolArr;
    }

    return out;
  }

  flattenFilterStructure() {
    return Object.values(Object.values(this.state.filters));
  }

  /* ---------------------------------------------------------
   * FILTER UPDATE FUNCTIONS
   * --------------------------------------------------------- */

  sendFilters({
                filter,
                idFilter,
              }: {
    filter: ToolFilter[];
    idFilter?: any[] | null;
  }) {
    const newFilter: any[] = [
      ...filter
        .map((tool, toolIdx) => {
          if (tool == null) return null;

          return tool.map((col, colIdx) => {
            return col?.values.map((val) => ({
              id: `${toolIdx}_${col.title}_${colIdx}`,
              value: val,
            }));
          });
        })
        .flat(3)
        .filter((x) => x != null),
    ];

    if (idFilter && idFilter.length > 0) {
      newFilter.push({ id: "id", values: idFilter });
    }

    this.props.addTypeToFilter(newFilter);
    this.props.setFilter(newFilter, true);
  }

  updateFilters(toolIdx: number, columnIdx: number, data: any) {
    const newFilters = [...this.state.filters];
    const idFilter = this.state.idFilters;

    newFilters[toolIdx] ??= [];
    newFilters[toolIdx][columnIdx] = data;

    this.setState({ filters: newFilters });
    this.sendFilters({ filter: newFilters, idFilter });
  }

  updateIdFilters(data: Record<string, any>) {
    const mapped = Object.keys(this.props.ids).map((i) => data[i]);

    const newFilter = mapped.some((i) => i !== "" && !isNil(i))
      ? mapped
      : undefined;

    this.setState({ idFilters: newFilter });

    this.sendFilters({ filter: this.state.filters, idFilter: newFilter });
  }

  /* ---------------------------------------------------------
   * RENDER
   * --------------------------------------------------------- */

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
            icon={faClose}
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

          {this.props.filterable.map((tool, idx) => (
            <FilterContainer
              key={`filtercontainer-${idx}`}
              resetFilterHook={this.resetFilterHook}
              updateFilters={(data, columnIndex) =>
                this.updateFilters(idx, columnIndex, data)
              }
              currentFilters={this.state.filters[idx] || []}
              toolName={tool.name}
              filters={tool.columns}
              hiddenCols={hiddenCols[idx]}
            />
          ))}
        </div>
      </div>
    );
  }
}
