// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import React from "react";
import equals from "deep-equal";
import { pathOr } from "../../utils/utils";
import "rc-slider/assets/index.css";

let debounceHandler = setTimeout(() => {}, 500);

export default class TaskFilterCard extends React.PureComponent {
  constructor(props: any) {
    super(props);
    this.state = {
      values: this.extractFilters(),
    };
    props.resetFilterHook(() => this.resetIdFilters());
  }

  resetIdFilters() {
    this.setState({ values: {} });
    this.sendFilterUpdate({});
  }

  sendFilterUpdate(values: any) {
    // @ts-expect-error TS(2339): Property 'updateFilters' does not exist on type 'R... Remove this comment to see the full error message
    this.props.updateFilters(values);
  }

  extractFilters() {
    let i = 0;
    const newVal = {};
    // @ts-expect-error TS(2339): Property 'ids' does not exist on type 'Readonly<{}... Remove this comment to see the full error message
    for (const id of Object.keys(this.props.ids)) {
      // @ts-expect-error TS(7053): Element implicitly has an 'any' type because expre... Remove this comment to see the full error message
      newVal[id] = pathOr(["filters", i++], "", this.props);
    }
    return newVal;
  }

  componentDidUpdate(prevProps: any) {
    // @ts-expect-error TS(2339): Property 'filters' does not exist on type 'Readonl... Remove this comment to see the full error message
    if (!equals(this.props.filters, prevProps.filters)) {
      const newVal = this.extractFilters();
      this.setState({ values: newVal });
    }
  }

  render() {
    // @ts-expect-error TS(2339): Property 'ids' does not exist on type 'Readonly<{}... Remove this comment to see the full error message
    const ids = this.props.ids || {};
    const makeHeader = () => (
      <div className="filter-card--header">
        <>
          <h4 className="title">Task filter</h4>
        </>
      </div>
    );

    const makeFilterBody = () => {
      const body = Object.entries(ids).map(([key, example]) => {
        // @ts-expect-error TS(2339): Property 'values' does not exist on type 'Readonly... Remove this comment to see the full error message
        const value = this.state.values[key] || "";
        const id = `text-task-${key}`;
        return (
          <div key={id} className="task-id-filters">
            <label htmlFor={id}>{key}</label>
            <br />
            <input
              type="text"
              name={id}
              // @ts-expect-error TS(2322): Type 'unknown' is not assignable to type 'string |... Remove this comment to see the full error message
              placeholder={example}
              value={value}
              onChange={({ target: { value: textValue } }) => {
                clearTimeout(debounceHandler);
                const newState = {
                  // @ts-expect-error TS(2339): Property 'values' does not exist on type 'Readonly... Remove this comment to see the full error message
                  values: { ...this.state.values, [key]: textValue },
                };
                debounceHandler = setTimeout(() => {
                  this.sendFilterUpdate({
                    // @ts-expect-error TS(2339): Property 'values' does not exist on type 'Readonly... Remove this comment to see the full error message
                    ...this.state.values,
                    [key]: textValue,
                  });
                }, 500);
                this.setState(newState);
              }}
            />
          </div>
        );
      });
      return <div className="filter-card--body">{body}</div>;
    };

    return (
      <div className="filterBox--container">
        <div className="filter-card">
          {makeHeader()}
          {makeFilterBody()}
        </div>
      </div>
    );
  }
}
