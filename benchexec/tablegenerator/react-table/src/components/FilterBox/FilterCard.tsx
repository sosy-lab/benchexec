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
  numericMaxTimeout: any;
  numericMinTimeout: any;
  constructor(props: any) {
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

  sendFilterUpdate(values: any) {
    // @ts-expect-error TS(2339): Property 'filter' does not exist on type 'Readonly... Remove this comment to see the full error message
    const { type, categories } = this.props.filter;
    if (
      categories &&
      categories.includes("empty ") &&
      !values.includes(statusForEmptyRows)
    ) {
      values = values.concat(statusForEmptyRows);
    }
    if (values.length === 0 && type === "status") {
      // @ts-expect-error TS(2339): Property 'onFilterUpdate' does not exist on type '... Remove this comment to see the full error message
      this.props.onFilterUpdate({
        values: [emptyStateValue],
        // @ts-expect-error TS(2339): Property 'title' does not exist on type 'Readonly<... Remove this comment to see the full error message
        title: this.state.title || this.props.title,
      });
    } else {
      // @ts-expect-error TS(2339): Property 'onFilterUpdate' does not exist on type '... Remove this comment to see the full error message
      this.props.onFilterUpdate({
        values,
        // @ts-expect-error TS(2339): Property 'title' does not exist on type 'Readonly<... Remove this comment to see the full error message
        title: this.state.title || this.props.title,
      });
    }
  }

  // @ts-expect-error TS(6133): 'prevState' is declared but its value is never rea... Remove this comment to see the full error message
  componentDidUpdate(prevProps: any, prevState: any) {
    // @ts-expect-error TS(2339): Property 'filter' does not exist on type 'Readonly... Remove this comment to see the full error message
    if (!this.props.filter) {
      return;
    }
    if (
      !prevProps.filter ||
      // @ts-expect-error TS(2339): Property 'filter' does not exist on type 'Readonly... Remove this comment to see the full error message
      prevProps.filter.values !== this.props.filter.values
    ) {
      const { values, number_of_significant_digits: significantDigits } =
        // @ts-expect-error TS(2339): Property 'filter' does not exist on type 'Readonly... Remove this comment to see the full error message
        this.props.filter;
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

  handleMinMaxValue(value: any, significantDigits: any) {
    const builder = new NumberFormatterBuilder(significantDigits).build();
    // @ts-expect-error TS(2339): Property 'filter' does not exist on type 'Readonly... Remove this comment to see the full error message
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

  handleNumberChange(min: any, max: any) {
    const newState = {};
    // @ts-expect-error TS(2339): Property 'sliderMin' does not exist on type '{}'.
    newState.sliderMin = Number(this.state.numericMin ?? this.state.sliderMin);
    // @ts-expect-error TS(2339): Property 'sliderMax' does not exist on type '{}'.
    newState.sliderMax = Number(this.state.numericMax ?? this.state.sliderMax);
    // @ts-expect-error TS(2339): Property 'sliderMin' does not exist on type '{}'.
    if (newState.sliderMin > newState.sliderMax) {
      // @ts-expect-error TS(2339): Property 'sliderMax' does not exist on type '{}'.
      const temp = newState.sliderMax;
      // @ts-expect-error TS(2339): Property 'sliderMax' does not exist on type '{}'.
      newState.sliderMax = newState.sliderMin;
      // @ts-expect-error TS(2339): Property 'sliderMin' does not exist on type '{}'.
      newState.sliderMin = temp;
    }
    // defaulting to an empty string per side, if the values exceeds
    // or is less than the min/max thresholds
    const stringRepMin =
      // @ts-expect-error TS(2339): Property 'sliderMin' does not exist on type '{}'.
      newState.sliderMin <= Number(min) ? "" : newState.sliderMin;
    const stringRepMax =
      // @ts-expect-error TS(2339): Property 'sliderMax' does not exist on type '{}'.
      newState.sliderMax >= Number(max) ? "" : newState.sliderMax;
    // @ts-expect-error TS(2339): Property 'values' does not exist on type '{}'.
    newState.values = [`${stringRepMin}:${stringRepMax}`];
    this.setState(newState);
    // @ts-expect-error TS(2339): Property 'values' does not exist on type '{}'.
    this.sendFilterUpdate(newState.values);
  }

  render() {
    // @ts-expect-error TS(2339): Property 'filter' does not exist on type 'Readonly... Remove this comment to see the full error message
    const { filter, editable, availableFilters } = this.props;
    const selectRef = React.createRef();
    const filterAddSelection = () => (
      <>
        <span style={{ marginLeft: "12px" }}>Add filter for: </span>
        <select
          className="filter-selection"
          defaultValue="-1"
          // @ts-expect-error TS(2322): Type 'RefObject<unknown>' is not assignable to typ... Remove this comment to see the full error message
          ref={selectRef}
          onChange={({ target: { value: idx } }) => {
            // @ts-expect-error TS(2367): This condition will always return 'false' since th... Remove this comment to see the full error message
            if (idx === -1) {
              return;
            }
            this.setState({ idx: -1, active: true });
            // @ts-expect-error TS(2571): Object is of type 'unknown'.
            selectRef.current.value = "-1"; // Reset preselected option to "Column"
            // @ts-expect-error TS(2339): Property 'addFilter' does not exist on type 'Reado... Remove this comment to see the full error message
            this.props.addFilter(idx);
          }}
        >
          <option value="-1" disabled>
            Column
          </option>
          {availableFilters.map(({ idx, display_title }: any) => (
            <option key={idx} value={idx}>
              {display_title}
            </option>
          ))}
        </select>
      </>
    );

    // @ts-expect-error TS(6133): 'name' is declared but its value is never read.
    const makeHeader = (name: any, editable: any) => (
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
                // @ts-expect-error TS(2339): Property 'removeFilter' does not exist on type 'Re... Remove this comment to see the full error message
                this.props.removeFilter();
              }}
            />
          </>
        )}
      </div>
    );

    const makeFilterBody = (filter: any) => {
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
            // @ts-expect-error TS(2339): Property 'filter' does not exist on type 'Readonly... Remove this comment to see the full error message
            {this.props.filter.categories &&
              // @ts-expect-error TS(2339): Property 'filter' does not exist on type 'Readonly... Remove this comment to see the full error message
              this.props.filter.categories.includes("empty ") && (
                <div className="filter-card--body--empty-rows">
                  Empty rows{" "}
                  <input
                    type="checkbox"
                    name={`empty-rows`}
                    // @ts-expect-error TS(2322): Type 'RefObject<unknown>' is not assignable to typ... Remove this comment to see the full error message
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
                .filter((category: any) => category !== "empty ")
                .sort()
                .map((category: any) => {
                  const ref = React.createRef();
                  return (
                    <li key={category}>
                      <input
                        type="checkbox"
                        name={`cat-${category}`}
                        checked={values.includes(category)}
                        // @ts-expect-error TS(2322): Type 'RefObject<unknown>' is not assignable to typ... Remove this comment to see the full error message
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
                        // @ts-expect-error TS(2571): Object is of type 'unknown'.
                        onClick={() => ref.current.click()}
                        className={category}
                      >
                        {category}
                      </label>
                    </li>
                  );
                })}
            </ul>
            Status
            <ul className="filter-card--body--list">
              {statuses.sort().map((status: any) => {
                const ref = React.createRef();
                return (
                  <li key={status}>
                    <input
                      type="checkbox"
                      name={`stat-${status}`}
                      // @ts-expect-error TS(2322): Type 'RefObject<unknown>' is not assignable to typ... Remove this comment to see the full error message
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
                      // @ts-expect-error TS(2571): Object is of type 'unknown'.
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
        // @ts-expect-error TS(2339): Property 'length' does not exist on type 'string |... Remove this comment to see the full error message
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
              // @ts-expect-error TS(2769): No overload matches this call.
              step={step}
              defaultValue={[Number(min), Number(max)]}
              value={[
                // @ts-expect-error TS(2339): Property 'sliderMin' does not exist on type 'Reado... Remove this comment to see the full error message
                Number(this.state.sliderMin),
                // @ts-expect-error TS(2339): Property 'sliderMax' does not exist on type 'Reado... Remove this comment to see the full error message
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
                  // @ts-expect-error TS(2339): Property 'numericMin' does not exist on type 'Read... Remove this comment to see the full error message
                  this.state.numericMin !== null
                    // @ts-expect-error TS(2339): Property 'numericMin' does not exist on type 'Read... Remove this comment to see the full error message
                    ? this.state.numericMin
                    // @ts-expect-error TS(2339): Property 'sliderMin' does not exist on type 'Reado... Remove this comment to see the full error message
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
                  // @ts-expect-error TS(2339): Property 'numericMax' does not exist on type 'Read... Remove this comment to see the full error message
                  this.state.numericMax !== null
                    // @ts-expect-error TS(2339): Property 'numericMax' does not exist on type 'Read... Remove this comment to see the full error message
                    ? this.state.numericMax
                    // @ts-expect-error TS(2339): Property 'sliderMax' does not exist on type 'Reado... Remove this comment to see the full error message
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
        // @ts-expect-error TS(2339): Property 'name' does not exist on type 'Readonly<{... Remove this comment to see the full error message
        {makeHeader(this.props.name, editable)}
        // @ts-expect-error TS(2339): Property 'filter' does not exist on type 'Readonly... Remove this comment to see the full error message
        {makeFilterBody(this.props.filter)}
      </div>
    );
  }
}
