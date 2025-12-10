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

interface FilterBoxProps {
headerComponent: Element | JSX.Element;
tableHeader: any;
tools: any;
selectColumn: (ev: any) => void;
filterable: any;
setFilter: (filter: any, runFilterLogic?: boolean) => void;
resetFilters: () => void;
filtered: any[];
visible: boolean;
hiddenCols: any[];
hide: () => void;
ids: any;
addTypeToFilter: (filters: any) => any;
}

interface FilterBoxState {
  filters: any[];
  idFilters: any;
}

export default class FilterBox extends React.PureComponent<FilterBoxProps, FilterBoxState> {
  private listeners: Array<() => void> = [];
  private resetFilterHook: (fun: () => void) => void;
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
    const empty: any[] = []; //Object.keys(this.props.ids).map(() => null);
    this.setState({ idFilters: empty });
    this.sendFilters({ filter: this.state.filters, idFilter: empty });
  }

  resetAllContainers() {
    this.listeners.forEach((fun) => fun());
  }

  retrieveIdFilters(filters: any[]) {
    const possibleIdFilter = filters.find((filter) => filter.id === "id");
    return possibleIdFilter ? possibleIdFilter.values : [];
  }

  createFiltersFromReactTableStructure(filters: any[]) {
    if (!filters || !filters.length) {
      return [];
    }

    const out: any[] = [];

    for (const { id, value } of filters.flat()) {
      if (id === "id") {
        continue;
      }
      const { tool, name: title, column } = decodeFilter(id) as {
        tool: number;
        name: string;
        column: number;
      };
      const toolArr = out[tool] || [];
      if (!toolArr[column]) {
        toolArr[column] = { title, values: [value] };
      } else {
        toolArr[column].values.push(value);
      }
      out[tool] = toolArr;
    }
    return out;
  }

  flattenFilterStructure() {
    return Object.values(Object.values(this.state.filters));
  }

  sendFilters({ filter, idFilter }: { filter: any[]; idFilter: any[] }) {
    const newFilter: ({ id: string; values: any; })[] = [
      ...filter
        .map((tool, toolIdx) => {
          if (tool === null || tool === undefined) {
            return null;
          }
          return tool.map((col: any, colIdx: any) => {
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

    this.props.addTypeToFilter(newFilter);
    this.props.setFilter(newFilter, true);
  }

  updateFilters(toolIdx: number, columnIdx: number, data: any) {
    //this.props.setFilter(newFilter);
    const newFilters = [...this.state.filters];
    const idFilter = this.state.idFilters;
    newFilters[toolIdx] = newFilters[toolIdx] || [];
    newFilters[toolIdx][columnIdx] = data;
    this.setState({ filters: newFilters });
    this.sendFilters({ filter: newFilters, idFilter });
  }

  updateIdFilters(data: any) {
    const mapped = Object.keys(this.props.ids).map((i) => data[i]);

    const newFilter = mapped.some((item) => item !== "" && !isNil(item))
      ? mapped
      : [];

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
