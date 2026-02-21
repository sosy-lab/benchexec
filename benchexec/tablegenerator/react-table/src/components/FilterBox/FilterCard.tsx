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
  emptyStateValue,
  getStep,
  NumberFormatterBuilder,
} from "../../utils/utils";
import { statusForEmptyRows } from "../../utils/filters";

const Range = createSliderWithTooltip(Slider.Range);

const numericInputDebounce = 500;
let debounceHandler: ReturnType<typeof setTimeout> = setTimeout(() => {
  /* empty */
}, numericInputDebounce);

/* ============================================================
 * Domain Types
 * ============================================================ */

type FilterType = "status" | "text" | "measure" | "number";

interface AvailableFilter {
  idx: number;
  display_title: string;
  title: string;
}

interface FilterDefinition {
  title: string;
  display_title: string;
  unit?: string;
  type: FilterType;
  number_of_significant_digits?: number;
  categories?: string[];
  statuses?: string[];
  values?: string[];
  min?: number;
  max?: number;
}

/* ============================================================
 * Component Types
 * ============================================================ */

interface FilterUpdatePayload {
  values: string[];
  title: string;
}

interface FilterCardProps {
  filter?: FilterDefinition;
  editable?: boolean;
  availableFilters?: AvailableFilter[];

  title?: string;
  name?: string;
  style?: React.CSSProperties;

  onFilterUpdate: (payload: FilterUpdatePayload) => void;
  addFilter?: (idx: number) => void;
  removeFilter?: () => void;
}

interface FilterCardState {
  title: string;
  values: string[];
  idx: number;
  active: boolean;
  selectedDistincts: string[];
  sliderMin: string | number;
  sliderMax: string | number;
  numericMin: string | number | null;
  numericMax: string | number | null;
}

export default class FilterCard extends React.PureComponent<
  FilterCardProps,
  FilterCardState
> {
  private numericMinTimeout: ReturnType<typeof setTimeout> | null = null;
  private numericMaxTimeout: ReturnType<typeof setTimeout> | null = null;

  // NOTE (JS->TS): Define ref as a stable class property instead of creating it in render()
  // to avoid creating a new ref instance on every render.
  private selectRef = React.createRef<HTMLSelectElement>();
  private emptyRowRef = React.createRef<HTMLInputElement>();

  constructor(props: FilterCardProps) {
    super(props);
    const { values, min, max, type } = props.filter || { values: [] };

    let sliderMin: string | number = 0;
    let sliderMax: string | number = 0;

    if (type === "measure" || type === "number") {
      const builder = this.getFormatter();
      sliderMin = builder(min ?? 0);
      sliderMax = builder(max ?? 0);
      const value = values && values[0];
      if (value && value.includes(":")) {
        const res = this.handleMinMaxValue(value);
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
      // NOTE (JS->TS): Replaced pathOr(...) with optional chaining and nullish coalescing to achieve the same safe fallback behavior in a type-safe way.
      idx: props.availableFilters?.[0]?.idx ?? 0,
      active: true,
      selectedDistincts: [],
      sliderMin,
      sliderMax,
      numericMin: null,
      numericMax: null,
    };
  }

  // NOTE (JS->TS): Centralizes the NumberFormatterBuilder creation.
  // In the original JS implementation, the builder logic (including the
  // significantDigits check) was duplicated in multiple places
  // (constructor, handleMinMaxValue, render).
  private getFormatter(): (n: number) => string {
    const { number_of_significant_digits: digits } = this.props.filter || {};
    return digits === null || digits === undefined
      ? (n: number) => n.toString()
      : new NumberFormatterBuilder(digits).build();
  }

  sendFilterUpdate(values: string[]): void {
    const { type, categories } = this.props.filter ?? {};
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
        title: this.state.title || this.props.title || "",
      });
    } else {
      this.props.onFilterUpdate({
        values,
        title: this.state.title || this.props.title || "",
      });
    }
  }

  componentDidUpdate(prevProps: FilterCardProps): void {
    if (!this.props.filter) {
      return;
    }
    if (
      !prevProps.filter ||
      prevProps.filter.values !== this.props.filter.values
    ) {
      const { values = [] } = this.props.filter;
      const [value] = values;
      if (value && value.includes(":")) {
        const { min, max } = this.handleMinMaxValue(value);
        this.setState({
          sliderMin: min,
          sliderMax: max,
          numericMin: min,
          numericMax: max,
        });
      }
    }
  }

  handleMinMaxValue(value: string): {
    min: string | number;
    max: string | number;
  } {
    const builder = this.getFormatter();
    const { min: propMin, max: propMax } = this.props.filter || {
      min: 0,
      max: Infinity,
    };
    const [vMin, vMax] = value.split(":");
    return {
      min: vMin.trim() !== "" ? vMin : builder(propMin ?? 0),
      max: vMax.trim() !== "" ? vMax : builder(propMax ?? Infinity),
    };
  }

  handleNumberChange(min: string | number, max: string | number): void {
    const sliderMin = Number(this.state.numericMin ?? this.state.sliderMin);
    const sliderMax = Number(this.state.numericMax ?? this.state.sliderMax);

    let finalSliderMin = sliderMin;
    let finalSliderMax = sliderMax;

    if (sliderMin > sliderMax) {
      finalSliderMin = sliderMax;
      finalSliderMax = sliderMin;
    }
    // defaulting to an empty string per side, if the values exceeds
    // or is less than the min/max thresholds
    const stringRepMin = finalSliderMin <= Number(min) ? "" : finalSliderMin;
    const stringRepMax = finalSliderMax <= Number(max) ? "" : finalSliderMax;
    const values = [`${stringRepMin}:${stringRepMax}`];

    this.setState({
      sliderMin: finalSliderMin,
      sliderMax: finalSliderMax,
      values,
    });
    this.sendFilterUpdate(values);
  }

  render(): React.ReactNode {
    const { filter, editable, availableFilters } = this.props;

    const filterAddSelection = () => (
      <>
        <span style={{ marginLeft: "12px" }}>Add filter for: </span>
        <select
          className="filter-selection"
          defaultValue="-1"
          ref={this.selectRef}
          onChange={({
            target: { value: idx },
          }: React.ChangeEvent<HTMLSelectElement>) => {
            // NOTE (JS->TS): Select values are strings; normalize to number for correct comparisons and callback typing.
            const numericIdx = Number(idx);
            if (numericIdx === -1) {
              return;
            }
            this.setState({ idx: -1, active: true });
            if (this.selectRef.current) {
              this.selectRef.current.value = "-1"; // Reset preselected option to "Column"
            }
            this.props.addFilter?.(numericIdx);
          }}
        >
          <option value="-1" disabled>
            Column
          </option>
          {availableFilters?.map(({ idx, display_title }) => (
            <option key={idx} value={idx}>
              {display_title}
            </option>
          ))}
        </select>
      </>
    );

    const makeHeader = (
      name: string | undefined,
      editable: boolean | undefined,
    ) => (
      <div className="filter-card--header">
        {editable ? (
          filterAddSelection()
        ) : (
          <>
            <h4 className="title">{`${filter?.display_title ?? ""} ${
              filter?.unit ? "(" + filter.unit + ")" : ""
            }`}</h4>
            <FontAwesomeIcon
              className="delete-button"
              icon={faTrash}
              onClick={() => {
                this.props.removeFilter?.();
              }}
            />
          </>
        )}
      </div>
    );

    const makeFilterBody = (filter: FilterDefinition | undefined) => {
      if (!filter) {
        return null;
      }
      const {
        title,
        type,
        categories = [],
        statuses = [],
        values = [],
      } = filter;

      const { min = 0, max = 0 } = filter;
      let body: React.ReactNode;

      if (type === "status") {
        body = (
          <>
            {this.props.filter?.categories &&
              this.props.filter.categories.includes("empty ") && (
                <div className="filter-card--body--empty-rows">
                  Empty rows{" "}
                  <input
                    type="checkbox"
                    name={`empty-rows`}
                    ref={this.emptyRowRef}
                    checked={values.includes("empty ")}
                    onChange={({
                      target: { checked },
                    }: React.ChangeEvent<HTMLInputElement>) => {
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
                  const ref = React.createRef<HTMLInputElement>();
                  return (
                    <li key={category}>
                      <input
                        type="checkbox"
                        name={`cat-${category}`}
                        checked={values.includes(category)}
                        ref={ref}
                        onChange={({
                          target: { checked },
                        }: React.ChangeEvent<HTMLInputElement>) => {
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
                        onClick={() => ref.current?.click()}
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
              {statuses.sort().map((status) => {
                const ref = React.createRef<HTMLInputElement>();
                return (
                  <li key={status}>
                    <input
                      type="checkbox"
                      name={`stat-${status}`}
                      ref={ref}
                      checked={values.includes(status)}
                      onChange={({
                        target: { checked },
                      }: React.ChangeEvent<HTMLInputElement>) => {
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
                      onClick={() => ref.current?.click()}
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
            onChange={({
              target: { value: textValue },
            }: React.ChangeEvent<HTMLInputElement>) => {
              clearTimeout(debounceHandler);
              this.setState({ values: [textValue] });
              debounceHandler = setTimeout(() => {
                this.sendFilterUpdate([textValue]);
              }, numericInputDebounce);
            }}
          />
        );
      } else {
        const builder = this.getFormatter();
        const formattedMin = builder(min ?? 0);
        const formattedMax = builder(max ?? 0);

        const minStep = getStep(formattedMin);
        const maxStep = getStep(formattedMax);

        // get the bigger step by length of string (== smaller step)
        const step =
          String(minStep).length > String(maxStep).length ? minStep : maxStep;
        // NOTE (JS->TS): rc-slider expects a numeric step; getStep may return a string for HTML input compatibility.
        const sliderStep = typeof step === "string" ? Number(step) : step;

        //shift the decimal
        body = (
          <>
            <div className="filter-card--range-container">
              <b>{formattedMin}</b>
              <b>{formattedMax}</b>
            </div>
            <Range
              min={Number(formattedMin)}
              max={Number(formattedMax)}
              step={sliderStep}
              defaultValue={[Number(formattedMin), Number(formattedMax)]}
              value={[
                Number(this.state.sliderMin),
                Number(this.state.sliderMax),
              ]}
              onChange={(value: number[]) => {
                const [nMin, nMax] = value;
                this.setState({
                  sliderMin: builder(nMin),
                  sliderMax: builder(nMax),
                });
              }}
              onAfterChange={(value: number[]) => {
                const [nMin, nMax] = value;
                const fMin = builder(nMin);
                const fMax = builder(nMax);
                const stringRepMin = fMin === formattedMin ? "" : fMin;
                const stringRepMax = fMax === formattedMax ? "" : fMax;
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
                onChange={({
                  target: { value },
                }: React.ChangeEvent<HTMLInputElement>) => {
                  if (this.numericMinTimeout) {
                    window.clearTimeout(this.numericMinTimeout);
                  }
                  this.setState({ numericMin: value });
                  this.numericMinTimeout = setTimeout(
                    () => this.handleNumberChange(formattedMin, formattedMax),
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
                onChange={({
                  target: { value },
                }: React.ChangeEvent<HTMLInputElement>) => {
                  if (this.numericMaxTimeout) {
                    clearTimeout(this.numericMaxTimeout);
                  }
                  this.setState({ numericMax: value });
                  this.numericMaxTimeout = setTimeout(
                    () => this.handleNumberChange(formattedMin, formattedMax),
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
