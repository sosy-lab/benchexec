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

  setFilter({ title, active, value }) {
    console.log("Container received", { title, active, value });
    this.setState({
      filters: this.state.filters.map((filter) =>
        filter.title === title
          ? { ...filter, filtered: active, value }
          : filter,
      ),
    });
  }

  render() {
    const filters = this.getActiveFilters();
    console.log("container rendered");
    return (
      <div className="filterBox--container">
        <h4>{this.state.toolName}</h4>
        {filters.length === 0 ? "No Filters set" : null}
        <br />
        <br />
        {this.state.addingFilter ? (
          <FilterCard
            availableFilters={this.state.filters.filter((i) => !i.filtered)}
            editable="true"
            onFilterUpdate={(vals) => this.setFilter(vals)}
          />
        ) : (
          <div className="filter-add-button">
            <FontAwesomeIcon
              icon={faPlus}
              onClick={() => this.setState({ addingFilter: true })}
            />
          </div>
        )}
      </div>
    );
  }
}
