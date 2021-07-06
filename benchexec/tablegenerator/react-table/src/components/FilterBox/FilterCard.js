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
import { statusForEmptyRows } from "../../utils/filters";

const Range = createSliderWithTooltip(Slider.Range);

const numericInputDebounce = 500;
let debounceHandler = setTimeout(() => {}, numericInputDebounce);

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
    let sliderMin = 0;
    let sliderMax = 0;
    if (type === "measure" || type === "number") {
      const builder = new NumberFormatterBuilder(significantDigits).build();
      sliderMin = builder(min);
      sliderMax = builder(max);
      const value = values && values[0];
      if (value && value.includes(":")) {
        const res = this.handleMinMaxValue(value, significantDigits);
        sliderMin = res.min;
        sliderMax = res.max;
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
      sliderMin,
      sliderMax,
      numericMin: null,
      numericMax: null,
    };
  }

  sendFilterUpdate(values) {
    const { type, categories } = this.props.filter;
    if (
      categories &&
      categories.includes("empty ") &&
      !values.includes(statusForEmptyRows)
    ) {
      values = values.concat(statusForEmptyRows);
    }
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
        this.setState({
          sliderMin: min,
          sliderMax: max,
          numericMin: min,
          numericMax: max,
        });
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
      min: vMin.trim() !== "" ? vMin : builder(propMin),
      max: vMax.trim() !== "" ? vMax : builder(propMax),
    };
  }

  handleNumberChange(min, max) {
    const newState = {};
    newState.sliderMin = Number(this.state.numericMin ?? this.state.sliderMin);
    newState.sliderMax = Number(this.state.numericMax ?? this.state.sliderMax);
    if (newState.sliderMin > newState.sliderMax) {
      const temp = newState.sliderMax;
      newState.sliderMax = newState.sliderMin;
      newState.sliderMin = temp;
    }
    // defaulting to an empty string per side, if the values exceeds
    // or is less than the min/max thresholds
    const stringRepMin =
      newState.sliderMin <= Number(min) ? "" : newState.sliderMin;
    const stringRepMax =
      newState.sliderMax >= Number(max) ? "" : newState.sliderMax;
    newState.values = [`${stringRepMin}:${stringRepMax}`];
    this.setState(newState);
    this.sendFilterUpdate(newState.values);
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
      const emptyRowRef = React.createRef();
      if (type === "status") {
        body = (
          <>
            {this.props.filter.categories &&
              this.props.filter.categories.includes("empty ") && (
                <div className="filter-card--body--empty-rows">
                  Empty rows{" "}
                  <input
                    type="checkbox"
                    name={`empty-rows`}
                    ref={emptyRowRef}
                    checked={values.includes("empty ")}
                    onChange={({ target: { checked } }) => {
                      const emptyValue = "empty ";
                      if (checked) {
                        const newValues = [...values, emptyValue];
                        this.setState({ values: newValues });
                        this.sendFilterUpdate(newValues);
                      } else {
                        const newValues = without(emptyValue, values);

                        this.setState({ values: newValues });
                        this.sendFilterUpdate(newValues);
                      }
                    }}
                  />
                </div>
              )}
            Category
            <ul className="filter-card--body--list">
              {categories
                .filter((category) => category !== "empty ")
                .sort()
                .map((category) => {
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
              {statuses.sort().map((status) => {
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
              }, numericInputDebounce);
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
                Number(this.state.sliderMin),
                Number(this.state.sliderMax),
              ]}
              onChange={([nMin, nMax]) => {
                this.setState({
                  sliderMin: builder(nMin),
                  sliderMax: builder(nMax),
                });
              }}
              onAfterChange={([nMin, nMax]) => {
                const fMin = builder(nMin);
                const fMax = builder(nMax);
                const stringRepMin = fMin === min ? "" : fMin;
                const stringRepMax = fMax === max ? "" : fMax;
                this.setState({
                  sliderMin: fMin,
                  sliderMax: fMax,
                  numericMin: nMin,
                  numericMax: nMax,
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
                value={
                  this.state.numericMin !== null
                    ? this.state.numericMin
                    : this.state.sliderMin
                }
                lang="en-US"
                step={step}
                onChange={({ target: { value } }) => {
                  if (this.numericMinTimeout) {
                    clearTimeout(this.numericMinTimeout);
                  }
                  this.setState({ numericMin: value });
                  this.numericMinTimeout = setTimeout(
                    () => this.handleNumberChange(min, max),
                    numericInputDebounce,
                  );
                }}
              />
              <input
                type="number"
                name={`inp-${title}-max`}
                step={step}
                lang="en-US"
                value={
                  this.state.numericMax !== null
                    ? this.state.numericMax
                    : this.state.sliderMax
                }
                onChange={({ target: { value } }) => {
                  if (this.numericMaxTimeout) {
                    clearTimeout(this.numericMaxTimeout);
                  }
                  this.setState({ numericMax: value });
                  this.numericMaxTimeout = setTimeout(
                    () => this.handleNumberChange(min, max),
                    numericInputDebounce,
                  );
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
