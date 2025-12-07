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

const classNames = require("classnames");

type IdFilter = {
  id: "id";
  values: any[];
};

type ValueFilter = {
  id: string;
  value: any;
};

type ReactTableFilter = IdFilter | ValueFilter;

type ColumnFilter = {
  title: string;
  values: any[];
};

type ToolFilters = Array<ColumnFilter | undefined>;

interface FilterableTool {
  name: string;
  columns: any[];
}

interface FilterBoxProps {
  filtered?: ReactTableFilter[];
  ids: Record<string, unknown>;
  addTypeToFilter: (filters: ReactTableFilter[]) => void;
  setFilter: (filters: ReactTableFilter[], replace: boolean) => void;
  hiddenCols?: any[][];
  visible: boolean;
  hide: () => void;
  headerComponent?: React.ReactNode;
  filterable: FilterableTool[];
}

interface FilterBoxState {
  filters: ToolFilters[];
  idFilters?: any[] | null;
}

export default class FilterBox extends React.PureComponent<FilterBoxProps, FilterBoxState> {
  listeners: Array<() => void>;
  resetFilterHook: (fun: () => void) => void;

  constructor(props: FilterBoxProps) {
    super(props);

    const { filtered } = props;

    this.listeners = [];

    this.resetFilterHook = (fun: () => void) => this.listeners.push(fun);

    this.state = {
      filters: this.createFiltersFromReactTableStructure(filtered),
      idFilters: this.retrieveIdFilters(filtered),
    };
  }

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

  resetIdFilters() {
    const empty: any[] | null = null; //Object.keys(this.props.ids).map(() => null);
    this.setState({ idFilters: empty });
    this.sendFilters({ filter: this.state.filters, idFilter: empty });
  }

  resetAllContainers() {
    this.listeners.forEach((fun) => fun());
  }

  retrieveIdFilters(filters: ReactTableFilter[] | undefined): any[] | undefined {
    if (!filters || !filters.length) {
      return [];
    }

    const possibleIdFilter = filters.find(
      (filter): filter is IdFilter =>
        filter.id === "id" && (filter as IdFilter).values !== undefined,
    );
    return possibleIdFilter ? possibleIdFilter.values : [];
  }

  createFiltersFromReactTableStructure(filters: ReactTableFilter[] | undefined): ToolFilters[] {
    if (!filters || !filters.length) {
      return [];
    }

    const outByTool: Record<string, ToolFilters> = {};

    const flattened: ReactTableFilter[] = Array.isArray((filters as any)[0])
      ? (filters as any).flat()
      : filters;

    for (const f of flattened) {
      if (f.id === "id") {
        continue;
      }

      const { id, value } = f as ValueFilter;
      const { tool, name, column } = decodeFilter(id) as {
        tool: string | number;
        name: string;
        column: string | number;
      };
      const title = name;

      const columnIndex = Number(column);
      if (!Number.isFinite(columnIndex)) {
        continue;
      }

      const toolId = String(tool);
      const toolArr: ToolFilters = outByTool[toolId] || [];

      if (!toolArr[columnIndex]) {
        toolArr[columnIndex] = { title, values: [value] };
      } else {
        toolArr[columnIndex]!.values.push(value);
      }
      outByTool[toolId] = toolArr;
    }
    return Object.values(outByTool);
  }

  flattenFilterStructure() {
    return Object.values(this.state.filters).flat();
  }

  sendFilters({ filter, idFilter }: { filter: ToolFilters[]; idFilter?: any[] | null }) {
    const newFilter: ReactTableFilter[] = [
      ...filter
        .map((tool, toolIdx) => {
          if (!tool) {
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
        .filter((i): i is ValueFilter => i !== null && i !== undefined),
    ];

    if (idFilter && idFilter.length > 0) {
      newFilter.push({ id: "id", values: idFilter });
    }

    this.props.addTypeToFilter(newFilter);
    this.props.setFilter(newFilter, true);
  }

  updateFilters(toolIdx: number, columnIdx: number, data: ColumnFilter) {
    //this.props.setFilter(newFilter);
    const newFilters = [...this.state.filters];
    const idFilter = this.state.idFilters;
    newFilters[toolIdx] = newFilters[toolIdx] || [];
    newFilters[toolIdx]![columnIdx] = data;
    this.setState({ filters: newFilters });
    this.sendFilters({ filter: newFilters, idFilter });
  }

  updateIdFilters(data: any) {
    const ids = this.props.ids || {};
    const mapped = Object.keys(ids).map((i) => (data as any)[i]);

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
            updateFilters={(data: any) => this.updateIdFilters(data)}
            resetFilterHook={this.resetFilterHook}
            filters={this.state.idFilters}
          />
          {this.props.filterable.map((tool: any, idx: any) => {
            return (
              <FilterContainer
                resetFilterHook={this.resetFilterHook}
                updateFilters={(data: any, columnIndex: any) =>
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
