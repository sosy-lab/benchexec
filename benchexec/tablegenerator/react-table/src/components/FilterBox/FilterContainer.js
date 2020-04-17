import React from "react";
import { faPlus } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";

export default class FilterContainer extends React.Component {
  constructor(props) {
    super(props);

    const { filters, toolName } = props;
    this.state = { filters, toolName };
  }

  getActiveFilters() {
    return this.state.filters.filter((item) => item.filtered);
  }

  render() {
    const filters = this.getActiveFilters();

    return (
      <div className="filterBox--container">
        <h4>{this.state.toolName}</h4>
        {filters.length === 0 ? "No Filters set" : null}
        <br />
        <br />
        <div className="filter-add-button">
          <FontAwesomeIcon icon={faPlus} />
        </div>
      </div>
    );
  }
}
