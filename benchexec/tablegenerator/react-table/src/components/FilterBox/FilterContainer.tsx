// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import React, { PureComponent } from "react";
import FilterCard from "./FilterCard";
import equals from "deep-equal";

interface Filter {
    filtering: boolean;
    touched: number;
    values: string[];
    display_title: string;
    numCards: number;
    type?: string;
    categories?: string[];
    statuses?: string[];
}

interface FilterContainerProps {
    filters: Filter[];
    toolName: string;
    currentFilters: Filter[];
    resetFilterHook: (callback: () => void) => void;
    updateFilters: (filterData: { title: string; values: string[] }, idx: number) => void;
    hiddenCols?: number[];
}

interface FilterContainerState {
    filters: Filter[];
    toolName: string;
    addingFilter: boolean;
    numCards: number;
}

export default class FilterContainer extends PureComponent<FilterContainerProps, FilterContainerState> {

    constructor(props: FilterContainerProps) {
        super(props);
        const { filters, toolName, currentFilters } = props;

        for (const idx in currentFilters) {
            filters[idx] = {
                ...filters[idx],
                ...currentFilters[idx],
                touched: filters[idx].touched + 1,
                filtering: true,
            };
        }

        this.props.resetFilterHook(() => this.resetAllFilters());

        this.state = { filters, toolName, addingFilter: false, numCards: 0 };
    }


    getActiveFilters(): Filter[] {
        return this.state.filters
            .filter((item) => item.filtering)
            .sort((a, b) => a.numCards - b.numCards);
    }


    setFilter({ title, values, filtering = true }: { title:string; values:string[]; filtering?: boolean }, idx:number): void {
        const prevFilters = this.state.filters;
        prevFilters[idx].values = values;
        prevFilters[idx].filtering = filtering;
        prevFilters[idx].touched += 1;

        this.setState({ filters: [...prevFilters] });

        this.props.updateFilters({ title, values }, idx);
    }


    addFilter(idx:number): void {
        const { filters:newFilterState, numCards } = this.state;

        const newFilter = { filtering:true, numCards:numCards, touched:0 };

        if (newFilterState[idx].type === "status") {
            newFilter.values = [
                ...newFilterState[idx].categories!,
                ...newFilterState[idx].statuses!,
            ];
        }

        newFilterState[idx] = { ...newFilterState[idx], ...newFilter };


        this.setState({
            filters:newFilterState,
            addingFilter:false,
            numCards:numCards + 1,
        });
    }


    resetAllFilters(): void {
        const setFilters = this.state.filters.filter((item) => item.filtering);
        const newFilterState = this.state.filters.map((filter) => ({
            ...filter,
            filtering:false,
            values:[]
        }));

        this.setState({ filters:[...newFilterState] });

        for (const filter of setFilters) {
            if (filter.values) {
                this.props.updateFilters(
                    { title : filter.display_title , values : [] },
                    filter.idx
                );
            }
        }
    }


    removeFilter(idx:number , title:string): void {
        const newFilterState = this.state.filters;

        newFilterState[idx].filtering=false;
        newFilterState[idx].values=[];

        this.setState({filters:[...newFilterState]});

        this.props.updateFilters({title , values : []}, idx);
    }


    componentDidUpdate(prevProps:{ currentFilters : Filter[] }): void {
        const { currentFilters } = this.props;

        if (!equals(prevProps.currentFilters , currentFilters)) {

            let { filters } = this.state;

            for (const idx in currentFilters) {
                filters[idx] = {
                    ...filters[idx],
                    ...currentFilters[idx],
                    touched : filters[idx].touched +1 ,
                    filtering:true
                };
            }

            filters=filters.map((filter , idx)=>{
                const toBeRemoved= !!(currentFilters [idx] || filter.touched===0);

                return{
                    ...filter,
                    filtering : toBeRemoved ,
                    values : toBeRemoved ? filter.values : []
                };
            });

            this.setState({filters:[...filters]});
        }
    }


    render(): JSX.Element {
        const filters=this.getActiveFilters();

        const hiddenCols=this.props.hiddenCols || [];

        const availableFilters=this.state.filters.filter(
            (i , idx)=> !i.filtering && !hiddenCols.includes(idx)
        );


        return (
            <div className="filterBox--container">
                <h4 className="section-header">{this.state.toolName}</h4>

                {filters.length >0 &&
                    filters.map((filter , idx)=>(
                        <FilterCard
                            onFilterUpdate={(val)=>this.setFilter(val , filter.idx)}
                            title={filter.display_title}
                            removeFilter={()=>this.removeFilter(filter.idx , filter.display_title)}
                            filter={filter}
                            key={`${this.props.toolName}-${filter.display_title}-${filter.numCards}`}
                        />
                    ))}

                {(availableFilters.length && (
                    <FilterCard
                        availableFilters={availableFilters}
                        editable="true"
                        style={{ marginBottom :20 }}
                        addFilter={(idx)=>this.addFilter(idx)}
                        onFilterUpdate={(vals)=>this.setFilter(vals)}
                    />
                )) || undefined}

                <br />
            </div>
        );
    }
}
