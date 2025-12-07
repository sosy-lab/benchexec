import classNames from "classnames";

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


export default class FilterBox extends React.PureComponent {
  constructor(props: any) {
    super(props);

    const { filtered } = props;

    this.listeners = [];

    this.resetFilterHook = (fun: any) => this.listeners.push(fun);

    this.state = {
      filters: this.createFiltersFromReactTableStructure(filtered),
      idFilters: this.retrieveIdFilters(filtered)
    };
  }

  componentDidUpdate(prevProps: Record<string, any>) {
    if (!equals(prevProps.filtered, this.props.filtered)) {
      this.setState({
        filters: this.createFiltersFromReactTableStructure(this.props.filtered),
        idFilters: this.retrieveIdFilters(this.props.filtered)
      });
    }
  }

  resetAllFilters() {
    this.resetAllContainers();
    this.resetIdFilters();
  }

  resetIdFilters() {
    const empty = null; //Object.keys(this.props.ids).map(() => null);
    this.setState({ idFilters: empty });
    this.sendFilters({ filter: this.state.filters, idFilter: empty });
  }

  resetAllContainers() {
    this.listeners.forEach((fun: any) => fun());
  }

  retrieveIdFilters(filters: Record<string, any>) {
    const possibleIdFilter = filters.find((filter: Record<string, any>) => filter.id === "id");
    return possibleIdFilter ? possibleIdFilter.values : [];
  }

  createFiltersFromReactTableStructure(filters: Record<string, any>) {
    if (!filters || !filters.length) {
      return [];
    }

    const out = [];

    for (const { id, value } of filters.flat()) {
      if (id === "id") {
        continue;
      }
      const { tool, name: title, column } = decodeFilter(id);
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

  sendFilters({ filter, idFilter }) {
    const newFilter = [
    ...filter.
    map((tool: Record<string, any>, toolIdx: any) => {
      if (tool === null || tool === undefined) {
        return null;
      }
      return tool.map((col: Record<string, any>, colIdx: any) => {
        return col.values.map((val: any) => ({
          id: `${toolIdx}_${col.title}_${colIdx}`,
          value: val
        }));
      });
    }).
    flat(3).
    filter((i: any) => i !== null && i !== undefined)];

    if (idFilter && idFilter.length > 0) {
      newFilter.push({ id: "id", values: idFilter });
    }

    this.props.addTypeToFilter(newFilter);
    this.props.setFilter(newFilter, true);
  }

  updateFilters(toolIdx: Record<string, any>, columnIdx: Record<string, any>, data: any) {
    //this.props.setFilter(newFilter);
    const newFilters = [...this.state.filters];
    const idFilter = this.state.idFilters;
    newFilters[toolIdx] = newFilters[toolIdx] || [];
    newFilters[toolIdx][columnIdx] = data;
    this.setState({ filters: newFilters });
    this.sendFilters({ filter: newFilters, idFilter });
  }

  updateIdFilters(data: Record<string, any>) {
    const mapped = Object.keys(this.props.ids).map((i: Record<string, any>) => data[i]);

    const newFilter = mapped.some((item: any) => item !== "" && !isNil(item)) ?
    mapped :
    undefined;

    this.setState({ idFilters: newFilter });

    this.sendFilters({ filter: this.state.filters, idFilter: newFilter });
  }

  render() {
    const hiddenCols = this.props.hiddenCols || [];
    return (
      <div
        className={classNames("filterBox", {
          "filterBox--hidden": !this.props.visible
        })}>
        
        <div className="filterBox--header">
          <FontAwesomeIcon
            icon={faClose}
            className="filterBox--header--icon"
            onClick={this.props.hide} />
          
          {this.props.headerComponent}
          <FontAwesomeIcon
            icon={faTrash}
            className="filterBox--header--reset-icon"
            onClick={() => this.resetAllFilters()} />
          
        </div>

        <div className="filter-card--container">
          <TaskFilterCard
            ids={this.props.ids}
            updateFilters={(data: any) => this.updateIdFilters(data)}
            resetFilterHook={this.resetFilterHook}
            filters={this.state.idFilters} />
          
          {this.props.filterable.map((tool: Record<string, any>, idx: Record<string, any>) => {
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
                key={`filtercontainer-${idx}`} />);


          })}
        </div>
      </div>);

  }
}