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
  constructor(props) {
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

  sendFilterUpdate(values) {
    this.props.updateFilters(values);
  }

  extractFilters() {
    let i = 0;
    const newVal = {};
    for (const id of Object.keys(this.props.ids)) {
      newVal[id] = pathOr(["filters", i++], "", this.props);
    }
    return newVal;
  }

  componentDidUpdate(prevProps) {
    if (!equals(this.props.filters, prevProps.filters)) {
      const newVal = this.extractFilters();
      this.setState({ values: newVal });
    }
  }

  render() {
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
        const value = this.state.values[key] || "";
        const id = `text-task-${key}`;
        return (
          <div key={id} className="task-id-filters">
            <label htmlFor={id}>{key}</label>
            <br />
            <input
              type="text"
              name={id}
              placeholder={example}
              value={value}
              onChange={({ target: { value: textValue } }) => {
                clearTimeout(debounceHandler);
                const newState = {
                  values: { ...this.state.values, [key]: textValue },
                };
                debounceHandler = setTimeout(() => {
                  this.sendFilterUpdate({
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
