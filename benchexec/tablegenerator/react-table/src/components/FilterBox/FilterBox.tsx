// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import React from "react";
import { faClose, faTrash } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import equals from "deep-equal";
import classNames from "classnames";

import FilterContainer from "./FilterContainer";
import TaskFilterCard from "./TaskFilterCard";
import { decodeFilter, isNil } from "../../utils/utils";
import { CurrentFilterUpdate, FilterDefinition } from "./types";

/* ============================================================
 * Domain Types
 * ============================================================
 */

type FilterableTool = {
  name: string;
  columns: FilterDefinition[];
};

type IncomingFilterEntry = {
  id: string;
  value: string;
  values?: string[];
};

type EncodedFilterEntry = {
  id: string;
  value: string;
};

type IdFilterEntry = {
  id: "id";
  values: string[];
};

type OutgoingFilterEntry = EncodedFilterEntry | IdFilterEntry;

interface DecodedFilterId {
  tool: number;
  name: string;
  column: number;
}

type ColumnFilterData = {
  title: string;
  values: string[];
};

type ToolFilterData = Array<ColumnFilterData | undefined>;

/* ============================================================
 * Component Types
 * ============================================================
 */

type FilterBoxProps = {
  filtered: IncomingFilterEntry[] | IncomingFilterEntry[][];

  ids: Record<string, string>;
  filterable: FilterableTool[];

  hiddenCols?: Array<number[] | undefined>;
  visible: boolean;

  hide: () => void;
  headerComponent?: React.ReactNode;

  addTypeToFilter: (filter: OutgoingFilterEntry[]) => void;
  setFilter: (filter: OutgoingFilterEntry[], doFiltering: boolean) => void;
};

type FilterBoxState = {
  filters: Array<ToolFilterData | undefined>;
  idFilters: string[] | null;
};

export default class FilterBox extends React.PureComponent<
  FilterBoxProps,
  FilterBoxState
> {
  private listeners: Array<() => void>;

  private resetFilterHook: (fn: () => void) => void;

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

  componentDidUpdate(prevProps: FilterBoxProps): void {
    if (!equals(prevProps.filtered, this.props.filtered)) {
      this.setState({
        filters: this.createFiltersFromReactTableStructure(this.props.filtered),
        idFilters: this.retrieveIdFilters(this.props.filtered),
      });
    }
  }

  resetAllFilters(): void {
    this.resetAllContainers();
    this.resetIdFilters();
  }

  resetIdFilters(): void {
    const empty = null; //Object.keys(this.props.ids).map(() => null);
    this.setState({ idFilters: empty });
    this.sendFilters({ filter: this.state.filters, idFilter: empty });
  }

  resetAllContainers(): void {
    this.listeners.forEach((fun) => fun());
  }

  retrieveIdFilters(filters: FilterBoxProps["filtered"]): string[] | null {
    const possibleIdFilter = filters
      .flat()
      .find((filter) => filter.id === "id");
    return possibleIdFilter?.values ?? null;
  }

  createFiltersFromReactTableStructure(
    filters: FilterBoxProps["filtered"],
  ): Array<ToolFilterData | undefined> {
    if (!filters || !filters.length) {
      return [];
    }

    const out: Array<ToolFilterData | undefined> = [];

    for (const { id, value } of filters.flat()) {
      if (id === "id") {
        continue;
      }
      const {
        tool,
        name: title,
        column,
      } = decodeFilter(id) as unknown as DecodedFilterId;
      const toolArr = out[tool] ?? [];
      if (!toolArr[column]) {
        toolArr[column] = { title, values: [value] };
      } else {
        toolArr[column]?.values.push(value);
      }
      out[tool] = toolArr;
    }
    return out;
  }

  flattenFilterStructure(): ColumnFilterData[] {
    return this.state.filters
      .flat()
      .filter((f): f is ColumnFilterData => Boolean(f));
  }

  sendFilters({
    filter,
    idFilter,
  }: {
    filter: Array<ToolFilterData | undefined>;
    idFilter: string[] | null;
  }): void {
    const newFilter: OutgoingFilterEntry[] = [
      ...filter
        .map((tool, toolIdx) => {
          if (tool === null || tool === undefined) {
            return null;
          }
          return tool.map((col, colIdx) => {
            if (!col) {
              return null;
            }
            return col.values.map((val) => ({
              id: `${toolIdx}_${col.title}_${colIdx}`,
              value: val,
            }));
          });
        })
        .flat(3)
        .filter((i): i is EncodedFilterEntry => i !== null && i !== undefined),
    ];

    if (idFilter && Array.isArray(idFilter) && idFilter.length > 0) {
      newFilter.push({ id: "id", values: idFilter });
    }

    this.props.addTypeToFilter(newFilter);
    this.props.setFilter(newFilter, true);
  }

  updateFilters(
    toolIdx: number,
    columnIdx: number,
    data: ColumnFilterData,
  ): void {
    //this.props.setFilter(newFilter);
    const newFilters = [...this.state.filters];
    const idFilter = this.state.idFilters;
    newFilters[toolIdx] = newFilters[toolIdx] ?? [];
    (newFilters[toolIdx] as ToolFilterData)[columnIdx] = data;
    this.setState({ filters: newFilters });
    this.sendFilters({ filter: newFilters, idFilter });
  }

  updateIdFilters(data: Record<string, string>): void {
    const mapped = Object.keys(this.props.ids).map((i) => data[i]);

    const newFilter = mapped.some((item) => item !== "" && !isNil(item))
      ? mapped
      : null;

    this.setState({ idFilters: newFilter });

    this.sendFilters({ filter: this.state.filters, idFilter: newFilter });
  }

  render(): React.ReactNode {
    const hiddenCols = this.props.hiddenCols ?? [];
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
            updateFilters={(data: Record<string, string>) =>
              this.updateIdFilters(data)
            }
            resetFilterHook={this.resetFilterHook}
            filters={this.state.idFilters}
          />
          {this.props.filterable.map((tool, idx) => {
            return (
              <FilterContainer
                resetFilterHook={this.resetFilterHook}
                updateFilters={(data: ColumnFilterData, columnIndex: number) =>
                  this.updateFilters(idx, columnIndex, data)
                }
                currentFilters={
                  (this.state.filters[idx] as unknown as Record<
                    number,
                    CurrentFilterUpdate
                  >) ?? []
                }
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
