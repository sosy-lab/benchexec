import React from "react";
import { faCheck } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import Slider, { createSliderWithTooltip } from "rc-slider";

const Range = createSliderWithTooltip(Slider.Range);

export default class FilterCard extends React.Component {
  constructor(props) {
    super(props);
    const { value } = props.filter || { value: undefined };
    let currentMin = 0;
    let currentMax = 0;
    if (value && value.includes(":")) {
      const res = this.handleMinMaxValue(value);
      currentMin = res.min;
      currentMax = res.max;
    }
    this.state = {
      title:
        props.availableFilters && props.availableFilters.length
          ? props.availableFilters[0].title
          : "",
      value: null,
      idx: 0,
      active: true,
      selectedDistincts: [],
      currentMin,
      currentMax,
    };
  }

  sendFilterUpdate(value) {
    this.props.onFilterUpdate({
      value: value,
      title: this.state.title || this.props.title,
    });
  }

  componentDidUpdate(prevProps) {
    console.log("filtercard updates", { prevProps, newProps: this.props });
    if (!this.props.filter) {
      return;
    }
    if (
      !prevProps.filter ||
      prevProps.filter.value !== this.props.filter.value
    ) {
      const { value } = this.props.filter;
      console.log("filtercard decided to update: ", value);
      if (value && value.includes(":")) {
        const { min, max } = this.handleMinMaxValue(value);
        console.log("settings state", { currentMin: min, currentMax: max });
        this.setState({ currentMin: min, currentMax: max });
      }
    }
  }

  handleMinMaxValue(value) {
    const { min: propMin, max: propMax } = this.props.filter || {
      min: 0,
      max: Infinity,
    };
    console.log("handleMinMaxValue", { propMin, propMax });
    const [vMin, vMax] = value.split(":");
    return {
      min: vMin.trim() !== "" ? Number(vMin) : propMin,
      max: vMax.trim() !== "" ? Number(vMax) : propMax,
    };
  }

  render() {
    const { filter, editable, availableFilters } = this.props;
    // console.log("FilterCard received", filter);
    const filterAddSelection = () => (
      <>
        <select
          class="filter-selection"
          onChange={(e) => this.setState({ idx: e.target.value, active: true })}
        >
          {availableFilters.map(({ idx, display_title }) => (
            <option value={idx}>{display_title}</option>
          ))}
        </select>
        <FontAwesomeIcon
          className="check-button"
          icon={faCheck}
          onClick={() => this.props.addFilter(this.state.idx)}
        />
      </>
    );

    const makeHeader = (name, editable) => (
      <div className="filter-card--header">
        {editable ? (
          filterAddSelection()
        ) : (
          <>
            <h4 className="title">{filter.display_title}</h4>
            <FontAwesomeIcon
              className="check-button"
              icon={faCheck}
              onClick={() => this.sendFilterUpdate()}
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
        distincts,
        min,
        max,
        categories,
        statuses,
        value,
      } = filter;
      let body;
      if (type === "status") {
        body = (
          <>
            <b>Category</b>
            <ul className="filter-card--body--list">
              {categories.map((category) => (
                <li key={category}>
                  <input
                    type="checkbox"
                    name={`cat-${category}`}
                    checked={category === value}
                    onChange={({ target: { checked } }) => {
                      console.log({ checked, category });
                      if (checked) {
                        this.setState({ value: category });
                        this.sendFilterUpdate(category);
                      } else {
                        this.setState({ value: null });
                        this.sendFilterUpdate(null);
                      }
                    }}
                  />
                  <label for={`cat-${category}`}>{category}</label>
                </li>
              ))}
            </ul>
            <b>Status</b>
            <ul className="filter-card--body--list">
              {statuses.map((status) => (
                <li key={status}>
                  <input
                    type="checkbox"
                    name={`stat-${status}`}
                    checked={status === value}
                    onChange={({ target: { checked } }) => {
                      console.log({ checked, status });
                      if (checked) {
                        this.setState({ value: status });
                        this.sendFilterUpdate(status);
                      } else {
                        this.setState({ value: null });
                        this.sendFilterUpdate(null);
                      }
                    }}
                  />
                  <label for={`stat-${status}`}>{status}</label>
                </li>
              ))}
            </ul>
          </>
        );
      } else if (type === "text") {
        body = (
          <ul className="filter-card--body--list">
            {distincts.map((status) => (
              <li key={status}>
                <input
                  type="checkbox"
                  name={`stat-${status}`}
                  checked={status === value}
                />
                <label for={`text-${status}`}>{status}</label>
              </li>
            ))}
          </ul>
        );
      } else {
        body = (
          <>
            <div className="filter-card--range-container">
              <b>{min}</b>
              <b>{max}</b>
            </div>
            <Range
              min={min}
              max={max}
              defaultValue={[min, max]}
              value={[this.state.currentMin, this.state.currentMax]}
              onChange={([nMin, nMax]) =>
                this.setState({ currentMin: nMin, currentMax: nMax })
              }
              onAfterChange={([nMin, nMax]) => {
                this.setState({
                  currentMin: nMin,
                  currentMax: nMax,
                  value: `${nMin}:${nMax}`,
                });
                this.sendFilterUpdate(`${nMin}:${nMax}`);
              }}
            />
            <div className="filter-card--range-input-fields">
              <label
                className="range-input-fields--min"
                for={`inp-${title}-min`}
              >
                minimum
              </label>
              <label
                className="range-input-fields--max"
                for={`inp-${title}-max`}
              >
                maximum
              </label>
              <input
                type="number"
                min={min}
                name={`inp-${title}-min`}
                value={this.state.currentMin}
                onChange={({ target: { value } }) => {
                  if (value > this.state.currentMax) {
                    this.setState({
                      currentMax: value,
                      currentMin: this.state.currentMax,
                      value: `${this.state.currentMax}:${value}`,
                    });
                  } else {
                    this.setState({
                      currentmin: value,
                      value: `${value}:${this.state.currentMax}`,
                    });
                  }
                }}
              />
              <input
                type="number"
                min={max}
                name={`inp-${title}-max`}
                value={this.state.currentMax}
                onChange={({ target: { value } }) => {
                  if (value < this.state.currentMin) {
                    this.setState({
                      currentMax: this.state.currentMin,
                      currentMin: value,
                      value: `${value}:${this.state.currentMin}`,
                    });
                  } else {
                    this.setState({
                      currentMax: value,
                      value: `${this.state.currentMin}:${value}`,
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
