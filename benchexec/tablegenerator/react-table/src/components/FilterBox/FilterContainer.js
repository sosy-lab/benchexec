import React from "react";
import { faPlus } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import FilterCard from "./FilterCard";

export default class FilterContainer extends React.Component {
  constructor(props) {
    super(props);

    const { filters, toolName } = props;
    this.state = { filters, toolName, addingFilter: false };
  }

  getActiveFilters() {
    return this.state.filters.filter((item) => item.filtered);
  }

  setFilter({ title, active, currentMin, currentMax }) {
    console.log("Container received", {
      title,
      active,
      currentMin,
      currentMax,
    });
    const newFilters = this.state.filters.map((filter) =>
      filter.title === title
        ? {
            ...filter,
            filtered: active,
            currentMin: Number(currentMin),
            currentMax: Number(currentMax),
          }
        : filter,
    );
    this.setState({
      addingFilter: false,
      filters: newFilters,
    });

    this.props.updateFilters(newFilters);
  }

  render() {
    const filters = this.getActiveFilters();
    console.log("container rendered");
    return (
      <div className="filterBox--container">
        <h4>{this.state.toolName}</h4>
        {filters.length === 0
          ? "No Filters set"
          : filters.map((filter) => (
              <FilterCard
                onFilterUpdate={(vals) => this.setFilter(vals)}
                title={filter.display_title}
                filter={filter}
                key={filter.title}
              />
            ))}
        <br />
        <br />
        {this.state.addingFilter ? (
          <FilterCard
            availableFilters={this.state.filters.filter((i) => !i.filtered)}
            editable="true"
            onFilterUpdate={(vals) => this.setFilter(vals)}
          />
        ) : (
          <div
            className="filter-add-button"
            onClick={() => this.setState({ addingFilter: true })}
          >
            <FontAwesomeIcon icon={faPlus} />
          </div>
        )}
      </div>
    );
  }
}
