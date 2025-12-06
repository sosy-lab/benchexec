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

export default class FilterBox extends React.PureComponent {
  listeners: any;
  resetFilterHook: any;
  constructor(props: any) {
    super(props);

    const { filtered } = props;

    this.listeners = [];

    this.resetFilterHook = (fun: any) => this.listeners.push(fun);

    this.state = {
      filters: this.createFiltersFromReactTableStructure(filtered),
      idFilters: this.retrieveIdFilters(filtered),
    };
  }

  componentDidUpdate(prevProps: any) {
    // @ts-expect-error TS(2339): Property 'filtered' does not exist on type 'Readon... Remove this comment to see the full error message
    if (!equals(prevProps.filtered, this.props.filtered)) {
      this.setState({
        // @ts-expect-error TS(2339): Property 'filtered' does not exist on type 'Readon... Remove this comment to see the full error message
        filters: this.createFiltersFromReactTableStructure(this.props.filtered),
        // @ts-expect-error TS(2339): Property 'filtered' does not exist on type 'Readon... Remove this comment to see the full error message
        idFilters: this.retrieveIdFilters(this.props.filtered),
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
    // @ts-expect-error TS(2339): Property 'filters' does not exist on type 'Readonl... Remove this comment to see the full error message
    this.sendFilters({ filter: this.state.filters, idFilter: empty });
  }

  resetAllContainers() {
    this.listeners.forEach((fun: any) => fun());
  }

  retrieveIdFilters(filters: any) {
    const possibleIdFilter = filters.find((filter: any) => filter.id === "id");
    return possibleIdFilter ? possibleIdFilter.values : [];
  }

  createFiltersFromReactTableStructure(filters: any) {
    if (!filters || !filters.length) {
      return [];
    }

    const out: any = [];

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
    // @ts-expect-error TS(2339): Property 'filters' does not exist on type 'Readonl... Remove this comment to see the full error message
    return Object.values(Object.values(this.state.filters));
  }

  sendFilters({ filter, idFilter }: any) {
    const newFilter = [
      ...filter
        .map((tool: any, toolIdx: any) => {
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
        .filter((i: any) => i !== null && i !== undefined),
    ];
    if (idFilter && idFilter.length > 0) {
      newFilter.push({ id: "id", values: idFilter });
    }

    // @ts-expect-error TS(2339): Property 'addTypeToFilter' does not exist on type ... Remove this comment to see the full error message
    this.props.addTypeToFilter(newFilter);
    // @ts-expect-error TS(2339): Property 'setFilter' does not exist on type 'Reado... Remove this comment to see the full error message
    this.props.setFilter(newFilter, true);
  }

  updateFilters(toolIdx: any, columnIdx: any, data: any) {
    //this.props.setFilter(newFilter);
    // @ts-expect-error TS(2339): Property 'filters' does not exist on type 'Readonl... Remove this comment to see the full error message
    const newFilters = [...this.state.filters];
    // @ts-expect-error TS(2339): Property 'idFilters' does not exist on type 'Reado... Remove this comment to see the full error message
    const idFilter = this.state.idFilters;
    newFilters[toolIdx] = newFilters[toolIdx] || [];
    newFilters[toolIdx][columnIdx] = data;
    this.setState({ filters: newFilters });
    this.sendFilters({ filter: newFilters, idFilter });
  }

  updateIdFilters(data: any) {
    // @ts-expect-error TS(2339): Property 'ids' does not exist on type 'Readonly<{}... Remove this comment to see the full error message
    const mapped = Object.keys(this.props.ids).map((i) => data[i]);

    const newFilter = mapped.some((item) => item !== "" && !isNil(item))
      ? mapped
      : undefined;

    this.setState({ idFilters: newFilter });

    // @ts-expect-error TS(2339): Property 'filters' does not exist on type 'Readonl... Remove this comment to see the full error message
    this.sendFilters({ filter: this.state.filters, idFilter: newFilter });
  }

  render() {
    // @ts-expect-error TS(2339): Property 'hiddenCols' does not exist on type 'Read... Remove this comment to see the full error message
    const hiddenCols = this.props.hiddenCols || [];
    return (
      <div
        className={classNames("filterBox", {
          // @ts-expect-error TS(2339): Property 'visible' does not exist on type 'Readonl... Remove this comment to see the full error message
          "filterBox--hidden": !this.props.visible,
        })}
      >
        <div className="filterBox--header">
          <FontAwesomeIcon
            icon={faClose}
            className="filterBox--header--icon"
            // @ts-expect-error TS(2339): Property 'hide' does not exist on type 'Readonly<{... Remove this comment to see the full error message
            onClick={this.props.hide}
          />
          // @ts-expect-error TS(2339): Property 'headerComponent' does not
          exist on type ... Remove this comment to see the full error message
          {this.props.headerComponent}
          <FontAwesomeIcon
            icon={faTrash}
            className="filterBox--header--reset-icon"
            onClick={() => this.resetAllFilters()}
          />
        </div>

        <div className="filter-card--container">
          <TaskFilterCard
            // @ts-expect-error TS(2322): Type '{ ids: any; updateFilters: (data: any) => vo... Remove this comment to see the full error message
            ids={this.props.ids}
            updateFilters={(data: any) => this.updateIdFilters(data)}
            resetFilterHook={this.resetFilterHook}
            // @ts-expect-error TS(2339): Property 'idFilters' does not exist on type 'Reado... Remove this comment to see the full error message
            filters={this.state.idFilters}
          />
          // @ts-expect-error TS(2339): Property 'filterable' does not exist on
          type 'Read... Remove this comment to see the full error message
          {this.props.filterable.map((tool: any, idx: any) => {
            return (
              <FilterContainer
                // @ts-expect-error TS(2322): Type '{ resetFilterHook: any; updateFilters: (data... Remove this comment to see the full error message
                resetFilterHook={this.resetFilterHook}
                updateFilters={(data: any, columnIndex: any) =>
                  this.updateFilters(idx, columnIndex, data)
                }
                // @ts-expect-error TS(2339): Property 'filters' does not exist on type 'Readonl... Remove this comment to see the full error message
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
