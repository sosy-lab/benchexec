import React from "react";
import { faCheck } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";

export default class FilterCard extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      title:
        props.availableFilters && props.availableFilters.length
          ? props.availableFilters[0].title
          : "",
      value: null,
      active: true,
      selectedDistincts: [],
      currentMin: (props.filter && props.filter.min) || 0,
      currentMax: (props.filter && props.filter.max) || 0,
    };
  }

  sendFilterUpdate() {
    this.props.onFilterUpdate({
      ...this.state,
      title: this.state.title || this.props.title,
    });
    console.log("Filtercard sent", this.state);
  }

  render() {
    const { filter, editable, availableFilters } = this.props;
    console.log("FilterCard received", filter);
    const filterAddSelection = () => (
      <>
        <select
          class="filter-selection"
          onChange={(e) =>
            this.setState({ title: e.target.value, active: true })
          }
        >
          {availableFilters.map((i) => (
            <option value={i.title}>{i.display_title}</option>
          ))}
        </select>
        <FontAwesomeIcon
          className="check-button"
          icon={faCheck}
          onClick={() => this.sendFilterUpdate()}
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
      const { title, type, distincts, min, max } = filter;
      let body;
      if (type === "status") {
        body = (
          <>
            <b>Category</b>
            <ul className="filter-card--body--list">
              <li>
                <input type="checkbox" name="cat-correct" />
                <label for="cat-correct">correct</label>
              </li>
              <li>
                <input type="checkbox" name="cat-error" />
                <label for="cat-correct">error</label>
              </li>
              <li>
                <input type="checkbox" name="cat-unknown" />
                <label for="cat-correct">unknown</label>
              </li>
              <li>
                <input type="checkbox" name="cat-wrong" />
                <label for="cat-correct">wrong</label>
              </li>
            </ul>
            <b>Status</b>
            <ul className="filter-card--body--list">
              {distincts.map((status) => (
                <li key={status}>
                  <input type="checkbox" name={`stat-${status}`} />
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
                <input type="checkbox" name={`stat-${status}`} />
                <label for={`text-${status}`}>{status}</label>
              </li>
            ))}
          </ul>
        );
      } else if (type === "count") {
        body = (
          <>
            <label for={`${title}-${type}-min`}>Minimum</label>
            <input
              type="number"
              min={min}
              max={this.state.currentMax}
              name={`${title}-${type}-min`}
              onBlur={(e) => this.setState({ currentMin: e.target.value })}
            />
            <label for={`${title}-${type}-max`}>Maximum</label>
            <input
              type="number"
              min={this.state.currentMin}
              max={max}
              onBlur={(e) => this.setState({ currentMax: e.target.value })}
              name={`${title}-${type}-max`}
            />
          </>
        );
      } else if (type === "measure") {
        body = (
          <>
            <label for={`${title}-${type}-min`}>Minimum</label>
            <input
              type="number"
              min={min}
              max={this.state.currentMax}
              name={`${title}-${type}-min`}
              value={this.state.currentMin}
              onChange={(e) => this.setState({ currentMin: e.target.value })}
            />
            <label for={`${title}-${type}-max`}>Maximum</label>
            <input
              type="number"
              min={this.state.currentMin}
              max={max}
              value={this.state.currentMax}
              onChange={(e) => this.setState({ currentMax: e.target.value })}
              name={`${title}-${type}-max`}
            />
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
