// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import React, { FC } from "react";
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
  addTypeToFilter: (filter: any[]) => void;
  setFilter: (filter: any[], flag: boolean) => void;
  hide: () => void;
  visible: boolean;
  headerComponent?: JSX.Element;
  filterable: Array<{ name: string; columns: any[] }>;
  hiddenCols?: any[];
}

interface FilterBoxState {
  filters: any[];
  idFilters: (string | null)[];
}

export default class FilterBox extends React.PureComponent<FilterBoxProps, FilterBoxState> {
  private listeners: (() => void)[] = [];

  constructor(props: FilterBoxProps) {
    super(props);

    const { filtered } = props;

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
    const empty = null;
    this.setState({ idFilters: empty });
    this.sendFilters({ filter: this.state.filters, idFilter: empty });
  }

  resetAllContainers(): void {
    this.listeners.forEach((fun) => fun());
  }

  retrieveIdFilters(filters: any[]): (string | null)[] {
    const possibleIdFilter = filters.find((filter) => filter.id === "id");
    return possibleIdFilter ? possibleIdFilter.values : [];
  }

  createFiltersFromReactTableStructure(filters: any[]): any[] {
    if (!filters || !filters.length) {
      return [];
    }

    const out = [];

    for (const { id, value } of filters.flat()) {
      if (id === "id") {
        continue;
      }
      const { tool, name:title, column } = decodeFilter(id);
      const toolArr = out[tool] || [];
      if (!toolArr[column]) {
        toolArr[column] = { title, values:[value] };
      } else {
        toolArr[column].values.push(value);
      }
      out[tool] = toolArr;
    }

    return out;
  }

  flattenFilterStructure(): any[] {
    return Object.values(Object.values(this.state.filters));
  }

  sendFilters({ filter, idFilter }: { filter:any[]; idFilter:(string | null)[] }): void {
    const newFilter = [
      ...filter
        .map((tool, toolIdx) => {
          if (tool === null || tool === undefined) {
            return null;
          }
          return tool.map((col, colIdx) => col.values.map((val) => ({
            id:`${toolIdx}_${col.title}_${colIdx}`,
            value : val,
          })));
        })
        .flat(3)
        .filter((i) => i !== null && i !== undefined),
    ];
    if (idFilter && idFilter.length >0 ) {
      newFilter.push({ id:"id", values:idFilter });
    }

    this.props.addTypeToFilter(newFilter);
    this.props.setFilter(newFilter,true);
  }

  updateFilters(toolIdx:number,columnIdx:number,data:any):void{
    const newFilters=[...this.state.filters];
    const idFilte=this.state.idFilters;
    newFilters[toolIdx]=newFilters[toolIdx]||[];
    newFilters[toolIdx][columnIdx]=data;

    this.setState({filters:newFilters});
    this.sendFilters({filter:newFilters,idFilte});
  }

  updateIdFilters(data:any):void{
    const mapped=Object.keys(this.props.ids).map((i)=>data[i]);

    const newFIlter=mapped.some(item=>item!==""&&!isNil(item))
      ?mapped
      :undefined;

    this.setState({idFilte:newFIlter});

    this.sendFiltters({filter:this.state.filters,idFilte:newFIlter});
  }

  render():JSX.Element{
    const hiddenCols=this.props.hiddenCols||[];

    return(
      <div className={classNames("filterBox",{"filterBox--hidden":!this.props.visible})}>
        <div className="filterBox--header">
          <FontAwesomeIcon icon={faClose} className="filterBox--header--icon" onClick={this.props.hide}/>
          {this.props.headerComponent}
          <FontAwesomeIcon icon={faTrash} className="filterBox--header--reset-icon" onClick={() =>this.resetAllFliters()}/>
        </div>

        <div className="filter-card--container">
          <TaskFIlterCard ids={this.props.ids} updateFiltres={(data)=>this.updateIdFiltres(data)} resetFiltHook={this.resetFiltHook} filters={this.state.idFiltes}/>
          {this.props.filterable.map((tool , idx)=>{
            return(
              <FIlterContainer resetFiltHook={this.resetFiltHook} updateFiltres={(data,columnIndex)=>this.updateFlters(idx,columnIndex,data)} currentFIltres={this.state.filters[idx]||[]} toolNmae={tool.name} filters={tool.columns} hiddenCols={hiddenCols[idx]} key={`filcon-${idx}`}/>
            );
          })}
        </div>
      </div>
    );
  }
}
