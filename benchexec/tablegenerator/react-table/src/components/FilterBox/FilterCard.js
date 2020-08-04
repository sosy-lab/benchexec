// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import React from "react";
import { faTrash } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import Slider, { createSliderWithTooltip } from "rc-slider";
import "rc-slider/assets/index.css";

import {
  without,
  pathOr,
  emptyStateValue,
  getStep,
  NumberFormatterBuilder,
} from "../../utils/utils";

const Range = createSliderWithTooltip(Slider.Range);

let debounceHandler = setTimeout(() => {}, 500);

export default class FilterCard extends React.PureComponent {
  constructor(props) {
    super(props);
    const {
      values,
      min,
      max,
      type,
      number_of_significant_digits: significantDigits,
    } = props.filter || { values: [] };
    let currentMin = 0;
    let currentMax = 0;
    if (type === "measure" || type === "number") {
      const builder = new NumberFormatterBuilder(significantDigits).build();
      currentMin = builder(min);
      currentMax = builder(max);
      const value = values && values[0];
      if (value && value.includes(":")) {
        const res = this.handleMinMaxValue(value, significantDigits);
        currentMin = res.min;
        currentMax = res.max;
      }
    }
    this.state = {
      title:
        props.availableFilters && props.availableFilters.length
          ? props.availableFilters[0].title
          : "",
      values: [],
      idx: pathOr(["availableFilters", 0, "idx"], 0, props),
      active: true,
      selectedDistincts: [],
      currentMin,
      currentMax,
    };
  }

  sendFilterUpdate(values) {
    const { type } = this.props.filter;
    if (values.length === 0 && type === "status") {
      this.props.onFilterUpdate({
        values: [emptyStateValue],
        title: this.state.title || this.props.title,
      });
    } else {
      this.props.onFilterUpdate({
        values,
        title: this.state.title || this.props.title,
      });
    }
  }

  componentDidUpdate(prevProps, prevState) {
    if (!this.props.filter) {
      return;
    }
    if (
      !prevProps.filter ||
      prevProps.filter.values !== this.props.filter.values
    ) {
      const {
        values,
        number_of_significant_digits: significantDigits,
      } = this.props.filter;
      const [value] = values;
      if (value && value.includes(":")) {
        const { min, max } = this.handleMinMaxValue(value, significantDigits);
        this.setState({ currentMin: min, currentMax: max });
      }
    }
  }

  handleMinMaxValue(value, significantDigits) {
    const builder = new NumberFormatterBuilder(significantDigits).build();
    const { min: propMin, max: propMax } = this.props.filter || {
      min: 0,
      max: Infinity,
    };
    const [vMin, vMax] = value.split(":");
    return {
      min: vMin.trim() !== "" ? builder(vMin) : builder(propMin),
      max: vMax.trim() !== "" ? builder(vMax) : builder(propMax),
    };
  }

  render() {
    const { filter, editable, availableFilters } = this.props;
    const selectRef = React.createRef();
    const filterAddSelection = () => (
      <>
        <span style={{ marginLeft: "12px" }}>Add filter for: </span>
        <select
          className="filter-selection"
          defaultValue="-1"
          ref={selectRef}
          onChange={({ target: { value: idx } }) => {
            if (idx === -1) {
              return;
            }
            this.setState({ idx: -1, active: true });
            selectRef.current.value = "-1"; // Reset preselected option to "Column"
            this.props.addFilter(idx);
          }}
        >
          <option value="-1" disabled>
            Column
          </option>
          {availableFilters.map(({ idx, display_title }) => (
            <option key={idx} value={idx}>
              {display_title}
            </option>
          ))}
        </select>
      </>
    );

    const makeHeader = (name, editable) => (
      <div className="filter-card--header">
        {editable ? (
          filterAddSelection()
        ) : (
          <>
            <h4 className="title">{`${filter.display_title} ${
              filter.unit ? "(" + filter.unit + ")" : ""
            }`}</h4>
            <FontAwesomeIcon
              className="delete-button"
              icon={faTrash}
              onClick={() => {
                this.props.removeFilter();
              }}
            />
          </>
        )}
      </div>
    );

    const makeFilterBody = (filter) => {
      if (!filter) {
        return null;
      }
      const {
        title,
        type,
        number_of_significant_digits: significantDigits,
        categories,
        statuses,
        values = [],
      } = filter;
      let { min, max } = filter;
      let body;
      if (type === "status") {
        body = (
          <>
            Category
            <ul className="filter-card--body--list">
              {categories.map((category) => {
                const ref = React.createRef();
                return (
                  <li key={category}>
                    <input
                      type="checkbox"
                      name={`cat-${category}`}
                      checked={values.includes(category)}
                      ref={ref}
                      onChange={({ target: { checked } }) => {
                        if (checked) {
                          const newValues = [...values, category];
                          this.setState({ values: newValues });
                          this.sendFilterUpdate(newValues);
                        } else {
                          const newValues = without(category, values);

                          this.setState({ values: newValues });
                          this.sendFilterUpdate(newValues);
                        }
                      }}
                    />
                    <label
                      htmlFor={`cat-${category}`}
                      onClick={() => ref.current.click()}
                    >
                      {category}
                    </label>
                  </li>
                );
              })}
            </ul>
            Status
            <ul className="filter-card--body--list">
              {statuses.map((status) => {
                const ref = React.createRef();
                return (
                  <li key={status}>
                    <input
                      type="checkbox"
                      name={`stat-${status}`}
                      ref={ref}
                      checked={values.includes(status)}
                      onChange={({ target: { checked } }) => {
                        if (checked) {
                          const newValues = [...values, status];
                          this.setState({ values: newValues });
                          this.sendFilterUpdate(newValues);
                        } else {
                          const newValues = without(status, values);
                          this.setState({ values: newValues });
                          this.sendFilterUpdate(newValues);
                        }
                      }}
                    />
                    <label
                      htmlFor={`stat-${status}`}
                      onClick={() => ref.current.click()}
                    >
                      {status}
                    </label>
                  </li>
                );
              })}
            </ul>
          </>
        );
      } else if (type === "text") {
        const [value] = values;

        body = (
          <input
            type="text"
            name={`text-${title}`}
            placeholder="Search for value"
            value={value}
            onChange={({ target: { value: textValue } }) => {
              clearTimeout(debounceHandler);
              this.setState({ values: [textValue] });
              debounceHandler = setTimeout(() => {
                this.sendFilterUpdate([textValue]);
              }, 500);
            }}
          />
        );
      } else {
        const builder = new NumberFormatterBuilder(significantDigits).build();
        min = builder(min);
        max = builder(max);
        const minStep = getStep(min);
        const maxStep = getStep(max);

        // get the bigger step by length of string (== smaller step)
        const step = minStep.length > maxStep.length ? minStep : maxStep;

        //shift the decimal
        body = (
          <>
            <div className="filter-card--range-container">
              <b>{min}</b>
              <b>{max}</b>
            </div>
            <Range
              min={Number(min)}
              max={Number(max)}
              step={step}
              defaultValue={[Number(min), Number(max)]}
              value={[
                Number(this.state.currentMin),
                Number(this.state.currentMax),
              ]}
              onChange={([nMin, nMax]) => {
                this.setState({
                  currentMin: builder(nMin),
                  currentMax: builder(nMax),
                });
              }}
              onAfterChange={([nMin, nMax]) => {
                const fMin = builder(nMin);
                const fMax = builder(nMax);
                const stringRepMin = fMin === min ? "" : fMin;
                const stringRepMax = fMax === max ? "" : fMax;
                this.setState({
                  currentMin: fMin,
                  currentMax: fMax,
                  values: [`${stringRepMin}:${stringRepMax}`],
                });
                this.sendFilterUpdate([`${stringRepMin}:${stringRepMax}`]);
              }}
            />
            <div className="filter-card--range-input-fields">
              <label
                className="range-input-fields--min"
                htmlFor={`inp-${title}-min`}
              >
                minimum
              </label>
              <label
                className="range-input-fields--max"
                htmlFor={`inp-${title}-max`}
              >
                maximum
              </label>
              <input
                type="number"
                name={`inp-${title}-min`}
                value={this.state.currentMin}
                lang="en-US"
                step={step}
                onChange={({ target: { value } }) => {
                  const { currentMin, currentMax } = this.state;
                  if (value > this.state.currentMax) {
                    const stringRepMin = currentMin === min ? "" : currentMin;
                    const stringRepMax = value === max ? "" : value;
                    this.setState({
                      currentMax: value,
                      currentMin: this.state.currentMax,
                      values: [`${stringRepMin}:${stringRepMax}`],
                    });
                  } else {
                    const stringRepMin = value === min ? "" : value;
                    const stringRepMax = currentMax === max ? "" : currentMax;
                    this.setState({
                      currentMin: value,
                      values: [`${stringRepMin}:${stringRepMax}`],
                    });
                  }
                }}
              />
              <input
                type="number"
                name={`inp-${title}-max`}
                step={step}
                lang="en-US"
                value={this.state.currentMax}
                onChange={({ target: { value } }) => {
                  const { currentMin, currentMax } = this.state;
                  if (value < this.state.currentMin) {
                    const stringRepMin = value === min ? "" : value;
                    const stringRepMax = currentMax === max ? "" : currentMax;
                    this.setState({
                      currentMax: this.state.currentMin,
                      currentMin: value,
                      values: [`${stringRepMin}:${stringRepMax}`],
                    });
                  } else {
                    const stringRepMin = currentMin === min ? "" : currentMin;
                    const stringRepMax = value === max ? "" : value;
                    this.setState({
                      currentMax: value,
                      values: [`${stringRepMin}:${stringRepMax}`],
                    });
                  }
                }}
              />
            </div>
          </>
        );
      }
      return <div className="filter-card--body">{body}</div>;
    };

    return (
      <div className="filter-card">
        {makeHeader(this.props.name, editable)}
        {makeFilterBody(this.props.filter)}
      </div>
    );
  }
}
