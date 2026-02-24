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
import {
  AvailableFilter,
  FilterUpdatePayload,
  FilterDefinition,
} from "./types";

const Range = createSliderWithTooltip(Slider.Range);

const numericInputDebounce = 500;

interface FilterCardProps {
  filter?: FilterDefinition;
  editable?: boolean;
  availableFilters?: AvailableFilter[];

  title?: string;
  name?: string;
  style?: React.CSSProperties;

  onFilterUpdate: (payload: FilterUpdatePayload, idx: number) => void;
  addFilter?: (idx: number) => void;
  removeFilter?: () => void;
}

interface FilterCardState {
  title: string;
  values: string[];
  idx: number;
  active: boolean;
  selectedDistincts: string[];
  sliderMin: string;
  sliderMax: string;
  // NOTE (JS->TS): Raw user input buffer for <input type="number">.
  // Keeps intermediate states like "", "-", "12." without breaking typing UX.
  inputMin: string;
  inputMax: string;
}

export default class FilterCard extends React.PureComponent<
  FilterCardProps,
  FilterCardState
> {
  private debounceHandler: ReturnType<typeof setTimeout> | null = null;
  private numericMinTimeout: ReturnType<typeof setTimeout> | null = null;
  private numericMaxTimeout: ReturnType<typeof setTimeout> | null = null;

  // NOTE (JS->TS): Define ref as a stable class property instead of creating it in render()
  // to avoid creating a new ref instance on every render.
  private selectRef = React.createRef<HTMLSelectElement>();
  private emptyRowRef = React.createRef<HTMLInputElement>();

  constructor(props: FilterCardProps) {
    super(props);
    const filter = props.filter;
    const values = filter?.values ?? [];
    const type = filter?.type;

    let sliderMin = "0";
    let sliderMax = "0";
    let inputMin = "";
    let inputMax = "";

    if (filter && (type === "measure" || type === "number")) {
      const builder = this.getFormatter();
      const { min, max } = filter;

      sliderMin = builder(min ?? 0);
      sliderMax = builder(max ?? 0);

      inputMin = sliderMin;
      inputMax = sliderMax;

      const value = values[0];
      if (value && value.includes(":")) {
        const res = this.handleMinMaxValue(value);
        sliderMin = res.min;
        sliderMax = res.max;
        inputMin = res.min;
        inputMax = res.max;
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
      inputMin,
      inputMax,
    };
  }

  // NOTE (JS->TS): Centralizes the NumberFormatterBuilder creation.
  // In the original JS implementation, the builder logic (including the
  // significantDigits check) was duplicated in multiple places
  // (constructor, handleMinMaxValue, render).
  private getFormatter(): (n: number) => string {
    if (!this.props.filter) {
      throw new Error("getFormatter called without filter");
    }

    // Keep JS behavior: significantDigits may be undefined.
    return new NumberFormatterBuilder(
      this.props.filter.number_of_significant_digits,
    ).build();
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
      this.props.onFilterUpdate(
        {
          values: [emptyStateValue],
          title: this.state.title || this.props.title || "",
        },
        this.state.idx,
      );
    } else {
      this.props.onFilterUpdate(
        {
          values,
          title: this.state.title || this.props.title || "",
        },
        this.state.idx,
      );
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
          inputMin: min,
          inputMax: max,
        });
      }
    }
  }

  handleMinMaxValue(value: string): { min: string; max: string } {
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

  handleNumberChange(minStr: string, maxStr: string): void {
    const min = Number(minStr);
    const max = Number(maxStr);

    const rawMin = this.state.inputMin;
    const rawMax = this.state.inputMax;

    // If user input isn't parseable yet (e.g. "", "-", "12.") do nothing.
    const nMin = rawMin.trim() === "" ? NaN : Number(rawMin);
    const nMax = rawMax.trim() === "" ? NaN : Number(rawMax);
    if (!Number.isFinite(nMin) || !Number.isFinite(nMax)) {
      return;
    }

    let finalMin = nMin;
    let finalMax = nMax;
    let nextInputMin = rawMin;
    let nextInputMax = rawMax;
    if (finalMin > finalMax) {
      [finalMin, finalMax] = [finalMax, finalMin];
      [nextInputMin, nextInputMax] = [rawMax, rawMin];
    }

    // defaulting to an empty string per side, if the values exceeds
    // or is less than the min/max thresholds
    const builder = this.getFormatter();
    const fMin = builder(finalMin);
    const fMax = builder(finalMax);

    const stringRepMin = finalMin <= min ? "" : fMin;
    const stringRepMax = finalMax >= max ? "" : fMax; // NOTE: likely you want >= for max threshold

    const values = [`${stringRepMin}:${stringRepMax}`];

    this.setState({
      sliderMin: fMin,
      sliderMax: fMax,
      inputMin: nextInputMin,
      inputMax: nextInputMax,
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
              if (this.debounceHandler) {
                clearTimeout(this.debounceHandler);
              }
              this.setState({ values: [textValue] });
              this.debounceHandler = setTimeout(() => {
                this.sendFilterUpdate([textValue]);
              }, numericInputDebounce);
            }}
          />
        );
      } else {
        const builder = this.getFormatter();
        const formattedMin = builder(min);
        const formattedMax = builder(max);

        const minStep = getStep(formattedMin);
        const maxStep = getStep(formattedMax);

        // get the bigger step by length of string (== smaller step)
        const step = minStep.length > maxStep.length ? minStep : maxStep;

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
              step={step as unknown as number}
              defaultValue={[Number(formattedMin), Number(formattedMax)]}
              value={[
                Number(this.state.sliderMin),
                Number(this.state.sliderMax),
              ]}
              onChange={(value: number[]) => {
                const [nMin, nMax] = value;
                const nextMin = builder(nMin);
                const nextMax = builder(nMax);

                this.setState({
                  sliderMin: nextMin,
                  sliderMax: nextMax,
                  inputMin: nextMin,
                  inputMax: nextMax,
                });
              }}
              onAfterChange={(value: number[]) => {
                const [nMin, nMax] = value;
                const fMin = builder(nMin);
                const fMax = builder(nMax);
                const stringRepMin = fMin === formattedMin ? "" : fMin;
                const stringRepMax = fMax === formattedMax ? "" : fMax;
                const values = [`${stringRepMin}:${stringRepMax}`];

                this.setState({
                  sliderMin: fMin,
                  sliderMax: fMax,
                  inputMin: fMin,
                  inputMax: fMax,
                  values,
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
                value={this.state.inputMin}
                lang="en-US"
                step={step}
                onChange={({
                  target: { value },
                }: React.ChangeEvent<HTMLInputElement>) => {
                  if (this.numericMinTimeout) {
                    window.clearTimeout(this.numericMinTimeout);
                  }
                  this.setState({ inputMin: value });
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
                value={this.state.inputMax}
                onChange={({
                  target: { value },
                }: React.ChangeEvent<HTMLInputElement>) => {
                  if (this.numericMaxTimeout) {
                    clearTimeout(this.numericMaxTimeout);
                  }
                  this.setState({ inputMax: value });
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
