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
let debounceHandler: number = window.setTimeout(() => {}, numericInputDebounce);

type FilterType = "status" | "text" | "measure" | "number" | string;

interface FilterDefinition {
  idx?: number;
  title?: string;
  display_title: string;
  type: FilterType;
  unit?: string;
  categories?: string[];
  statuses?: string[];
  values?: string[];
  min?: number;
  max?: number;
  number_of_significant_digits?: number;
  touched: number;
  filtering: boolean;
  numCards: number;
}

interface FilterCardProps {
  filter?: FilterDefinition;
  title?: string;
  name?: string;
  onFilterUpdate: (val: { values: string[]; title: string }) => void;
  removeFilter?: () => void;
  availableFilters?: Array<{
    idx: number;
    title: string;
    display_title: string;
  }>;
  addFilter?: (idx: number) => void;
  editable?: boolean | string;
  style?: React.CSSProperties;
}

interface FilterCardState {
  title: string;
  values: string[];
  idx: number;
  active: boolean;
  selectedDistinct: string[];
  sliderMin: number | string;
  sliderMax: number | string;
  numericMin: number | null;
  numericMax: number | null;
}

export default class FilterCard extends React.PureComponent<FilterCardProps, FilterCardState> {
  numericMaxTimeout: number | null = null;
  numericMinTimeout: number | null = null;

  constructor(props: FilterCardProps) {
    super(props);
    const {
      values = [],
      min,
      max,
      type,
      number_of_significant_digits: significantDigits,
    } = props.filter || { values: [] as string[] };

    let sliderMin: number | string = 0;
    let sliderMax: number | string = 0;

    if (type === "measure" || type === "number") {
      const builder = new NumberFormatterBuilder(
        significantDigits,
      ).build() as (n: number | undefined) => number | string;
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
      selectedDistinct: [],
      sliderMin,
      sliderMax,
      numericMin: null,
      numericMax: null,
    };
  }

  private get effectiveTitle(): string {
    const { filter, title: propsTitle } = this.props;
    return this.state.title || propsTitle || filter?.title || "";
  }

  sendFilterUpdate(values: string[]) {
    const { filter } = this.props;
    const type = filter?.type;
    const categories = filter?.categories;

    let newValues = values;

    if (
      categories &&
      categories.includes("empty ") &&
      !newValues.includes(statusForEmptyRows)
    ) {
      newValues = newValues.concat(statusForEmptyRows);
    }

    const title = this.effectiveTitle;

    if (newValues.length === 0 && type === "status") {
      this.props.onFilterUpdate({
        values: [emptyStateValue],
        title,
      });
    } else {
      this.props.onFilterUpdate({
        values: newValues,
        title,
      });
    }
  }

  componentDidUpdate(prevProps: FilterCardProps) {
    const currentFilter = this.props.filter;
    if (!currentFilter) {
      return;
    }

    if (!prevProps.filter || prevProps.filter.values !== currentFilter.values) {
      const {
        values = [],
        number_of_significant_digits: significantDigits
      } = currentFilter;
      const [value] = values;
      if (value && value.includes(":")) {
        const { min, max } = this.handleMinMaxValue(value, significantDigits);
        this.setState({
          sliderMin: min,
          sliderMax: max,
          numericMin: Number(min),
          numericMax: Number(max),
        });
      }
    }
  }

  handleMinMaxValue(value: string, significantDigits?: number) {
    const builder = new NumberFormatterBuilder(significantDigits).build() as (n: number | undefined) => number | string;
    const { filter } = this.props;
    const { min: propMin = 0, max: propMax = Infinity } = filter || {
      min: 0,
      max: Infinity,
    };
    const [vMin, vMax] = value.split(":");
    return {
      min: vMin.trim() !== "" ? vMin : builder(propMin),
      max: vMax.trim() !== "" ? vMax : builder(propMax),
    };
  }

  handleNumberChange(min: number | string, max: number | string) {
    const currentMin = Number(this.state.numericMin ?? this.state.sliderMin);
    const currentMax = Number(this.state.numericMax ?? this.state.sliderMax);

    let sliderMin = currentMin;
    let sliderMax = currentMax;

    if (sliderMin > sliderMax) {
      const temp = sliderMax;
      sliderMax = sliderMin;
      sliderMin = temp;
    }

    // defaulting to an empty string per side if the values exceed
    // or are less than the min/max thresholds
    const numericMin = sliderMin;
    const numericMax = sliderMax;

    const stringRepMin = numericMin <= Number(min) ? "" : numericMin.toString();
    const stringRepMax = numericMax >= Number(max) ? "" : numericMax.toString();

    const values = [`${stringRepMin}:${stringRepMax}`];

    this.setState({
      sliderMin,
      sliderMax,
      numericMin,
      numericMax,
      values,
    });

    this.sendFilterUpdate(values);
  }

  render() {
    const { filter, editable, availableFilters, style } = this.props;
    const selectRef = React.createRef<HTMLSelectElement>();

    const filterAddSelection = () => (
      <>
        <span style={{ marginLeft: "12px" }}>Add filter for: </span>
        <select
          className="filter-selection"
          defaultValue="-1"
          ref={selectRef}
          onChange={({ target: { value: idx } }) => {
            if (idx === "-1") {
              return;
            }
            this.setState({ idx: -1, active: true });
            if (selectRef.current) {
              selectRef.current.value = "-1"; // Reset the preselected option to "Column"
            }
            this.props.addFilter?.(Number(idx));
          }}
        >
          <option value="-1" disabled>
            Column
          </option>
          {(availableFilters || []).map(({ idx, display_title }: any) => (
            <option key={idx} value={idx}>
              {display_title}
            </option>
          ))}
        </select>
      </>
    );

    const makeHeader = () => (
      <div className="filter-card--header">
        {editable ? (
          filterAddSelection()
        ) : filter ? (
          <>
            <h4 className="title">{`${filter.display_title} ${
              filter.unit ? "(" + filter.unit + ")" : ""
            }`}</h4>
            <FontAwesomeIcon
              className="delete-button"
              icon={faTrash}
              onClick={() => {
                this.props.removeFilter?.();
              }}
            />
          </>
        ) : null }
      </div>
    );

    const makeFilterBody = (currentFilter?: FilterDefinition) => {
      if (!currentFilter) {
        return null;
      }

      const {
        title,
        type,
        number_of_significant_digits: significantDigits,
        categories = [],
        statuses = [],
        values = [],
      } = currentFilter;
      let body: React.ReactNode;
      const emptyRowRef = React.createRef<HTMLInputElement>();

      if (type === "status") {
        body = (
          <>
            {this.props.filter?.categories &&
              this.props.filter.categories.includes("empty ") && (
                <div className="filter-card--body--empty-rows">
                  Empty rows{" "}
                  <input
                    type="checkbox"
                    name="empty-rows"
                    ref={emptyRowRef}
                    checked={values.includes("empty ")}
                    onChange={({ target: { checked } }) => {
                      const emptyValue = "empty ";
                      const newValues = checked
                        ? [...values, emptyValue]
                        : without(emptyValue, values);
                      this.setState({ values: newValues });
                      this.sendFilterUpdate(newValues);
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
                        onChange={({ target: { checked } }) => {
                          const newValues = checked
                            ? [...values, category]
                            : without(category, values);
                          this.setState({ values: newValues });
                          this.sendFilterUpdate(newValues);
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
                      onChange={({ target: { checked } }) => {
                        const newValues = checked
                          ? [...values, status]
                          : without(status, values);
                        this.setState({ values: newValues });
                        this.sendFilterUpdate(newValues);
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
        const [value = ""] = values;

        body = (
          <input
            type="text"
            name={`text-${title}`}
            placeholder="Search for value"
            value={value}
            onChange={({ target: { value: textValue } }) => {
              clearTimeout(debounceHandler);
              this.setState({ values: [textValue] });
              debounceHandler = window.setTimeout(() => {
                this.sendFilterUpdate([textValue]);
              }, numericInputDebounce);
            }}
          />
        );
      } else {
        const builder = new NumberFormatterBuilder(significantDigits).build() as (n: number | undefined) => number | string;

        let { min, max } = currentFilter as { min?: number | string, max?: number | string };

        min = builder(typeof min === "number" ? min : Number(min));
        max = builder(typeof max === "number" ? max : Number(max));

        const minStepRaw = getStep(min as number | string);
        const maxStepRaw = getStep(max as number | string);

        const minStepStr = String(minStepRaw);
        const maxStepStr = String(maxStepRaw);

        // get the bigger step by length of string (== smaller step)
        const stepStr =
          minStepStr.length > maxStepStr.length
            ? minStepStr
            : maxStepStr;
        const step = Number(stepStr) || 1;

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
                const newValues = [`${stringRepMin}:${stringRepMax}`];
                this.setState({
                  sliderMin: fMin,
                  sliderMax: fMax,
                  numericMin: nMin,
                  numericMax: nMax,
                  values: newValues,
                });
                this.sendFilterUpdate(newValues);
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
                  this.setState({ numericMin: Number(value) });
                  this.numericMinTimeout = window.setTimeout(
                    () => this.handleNumberChange(min!, max!),
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
                  if (this.numericMaxTimeout !== null) {
                    clearTimeout(this.numericMaxTimeout);
                  }
                  this.setState({ numericMax: Number(value) });
                  this.numericMaxTimeout = window.setTimeout(
                    () => this.handleNumberChange(min!, max!),
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
      <div className="filter-card" style={style}>
        {makeHeader()}
        {makeFilterBody(filter)}
      </div>
    );
  }
}
