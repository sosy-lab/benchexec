import React from "react";
import { faPlus } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import FilterCard from "./FilterCard";

export default class FilterContainer extends React.Component {
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

  setFilter({ title, value }, idx) {
    console.log("Container received", {
      title,
      value,
      idx,
    });
    this.props.updateFilters({ title, value }, idx);
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
    newFilterState[idx].value = null;

    this.setState({ filters: newFilterState });
  }

  componentDidUpdate({ currentFilters: prevFilters }) {
    const { currentFilters } = this.props;
    if (prevFilters !== currentFilters) {
      // update set filters
      const { filters } = this.state;
      filters.forEach((item) => (item.filtering = false));
      for (const idx in currentFilters) {
        filters[idx] = {
          ...filters[idx],
          ...currentFilters[idx],
          filtering: currentFilters[idx].value !== "all ",
        };
      }
      this.setState({ filters });
    }
  }

  render() {
    console.log({ currentFilters: this.props.currentFilters });
    const filters = this.getActiveFilters();
    console.log({ activeFilters: filters });
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
                key={filter.numCards}
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
