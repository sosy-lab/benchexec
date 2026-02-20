// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import React from "react";
import equals from "deep-equal";
import "rc-slider/assets/index.css";

type TaskIdExamples = Record<string, string>;

type TaskIdFilterValues = Record<string, string>;

interface TaskFilterCardProps {
  ids?: TaskIdExamples;
  filters?: string[] | null;
  updateFilters: (values: TaskIdFilterValues) => void;
  resetFilterHook: (resetFn: () => void) => void;
}

interface TaskFilterCardState {
  values: TaskIdFilterValues;
}

export default class TaskFilterCard extends React.PureComponent<
  Readonly<TaskFilterCardProps>,
  Readonly<TaskFilterCardState>
> {
  private debounceHandler?: ReturnType<typeof setTimeout>;

  constructor(props: TaskFilterCardProps) {
    super(props);
    this.state = {
      values: this.extractFilters(),
    };
    props.resetFilterHook(() => this.resetIdFilters());
  }

  resetIdFilters(): void {
    this.setState({ values: {} });
    this.sendFilterUpdate({});
  }

  sendFilterUpdate(values: TaskIdFilterValues): void {
    this.props.updateFilters(values);
  }

  extractFilters(): TaskIdFilterValues {
    // NOTE (JS->TS): Directly access filters array and convert to TaskIdFilterValues object for better type safety and readability.
    // Using forEach and optional chaining eliminates the need for external pathOr utility and manual type casting.
    const newVal: TaskIdFilterValues = {};
    const ids = this.props.ids ?? {};
    const filters = this.props.filters;
    Object.keys(ids).forEach((id, i) => {
      newVal[id] = filters?.[i] ?? "";
    });
    return newVal;
  }

  componentDidUpdate(prevProps: Readonly<TaskFilterCardProps>): void {
    if (!equals(this.props.filters, prevProps.filters)) {
      const newVal = this.extractFilters();
      this.setState({ values: newVal });
    }
  }

  render(): React.ReactNode {
    const ids = this.props.ids ?? {};
    const makeHeader = () => (
      <div className="filter-card--header">
        <>
          <h4 className="title">Task filter</h4>
        </>
      </div>
    );

    const makeFilterBody = () => {
      const body = Object.entries(ids).map(([key, example]) => {
        const value = this.state.values[key] ?? "";
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
              onChange={({
                target: { value: textValue },
              }: React.ChangeEvent<HTMLInputElement>) => {
                // NOTE (JS->TS): Use a class-level debounce handler to avoid global side effects and ensure multiple instances
                // of this component don't interfere with each other's timers.
                if (this.debounceHandler) {
                  clearTimeout(this.debounceHandler);
                }
                const newState: TaskFilterCardState = {
                  values: { ...this.state.values, [key]: textValue },
                };
                this.debounceHandler = setTimeout(() => {
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
