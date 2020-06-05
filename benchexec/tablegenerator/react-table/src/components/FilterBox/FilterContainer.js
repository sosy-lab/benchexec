import React from "react";
import { faPlus } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import FilterCard from "./FilterCard";
import { equals } from "ramda";

export default class FilterContainer extends React.PureComponent {
  constructor(props) {
    super(props);
    const { filters, toolName } = props;
    this.state = { filters, toolName, addingFilter: false, numCards: 0 };
  }

  getActiveFilters() {
    return this.state.filters
      .filter((item) => item.filtering)
      .sort((a, b) => a.numCards - b.numCards);
  }

  setFilter({ title, values }, idx) {
    console.log("Container received", {
      title,
      values,
      idx,
    });
    const prevFilters = this.state.filters;
    prevFilters[idx].values = values;
    this.setState({ filters: [...prevFilters] });
    this.props.updateFilters({ title, values }, idx);
  }

  addFilter(idx) {
    const { filters: newFilterState, numCards } = this.state;
    console.log({ newFilterState, idx });
    newFilterState[idx].filtering = true;
    newFilterState[idx].numCards = numCards;

    this.setState({
      filters: newFilterState,
      addingFilter: false,
      numCards: numCards + 1,
    });
  }

  removeFilter(idx) {
    const newFilterState = this.state.filters;
    newFilterState[idx].filtering = false;
    newFilterState[idx].values = [];

    this.setState({ filters: newFilterState });
  }

  componentDidUpdate({ currentFilters: prevFilters }) {
    const { currentFilters } = this.props;
    if (!equals(prevFilters, currentFilters)) {
      // update set filters
      console.log("updated container");
      const { filters } = this.state;
      filters.forEach((item) => (item.filtering = false));
      for (const idx in currentFilters) {
        filters[idx] = {
          ...filters[idx],
          ...currentFilters[idx],
          filtering: currentFilters[idx].value !== "all ", // TODO
        };
      }
      this.setState({ filters: [...filters] });
    }
  }

  render() {
    const filters = this.getActiveFilters();
    console.log("container rendered");
    return (
      <div className="filterBox--container">
        <h4>{this.state.toolName}</h4>
        {filters.length === 0
          ? "No Filters set"
          : filters.map((filter, idx) => (
              <FilterCard
                onFilterUpdate={(val) => this.setFilter(val, filter.idx)}
                title={filter.display_title}
                filter={filter}
                key={`${this.props.toolName}-${filter.display_title}-${filter.numCards}`}
              />
            ))}
        <br />
        <br />
        {this.state.addingFilter ? (
          <FilterCard
            availableFilters={this.state.filters.filter((i) => !i.filtering)}
            editable="true"
            addFilter={(idx) => this.addFilter(idx)}
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
