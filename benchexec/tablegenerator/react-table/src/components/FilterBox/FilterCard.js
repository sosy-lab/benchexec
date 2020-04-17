import React from "react";
import { faCheck } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";

export default class FilterCard extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      title: props.availableFilters.length
        ? props.availableFilters[0].title
        : "",
      value: null,
      active: true,
    };
  }

  sendFilterUpdate() {
    this.props.onFilterUpdate({ ...this.state });
    console.log("Filtercard sent", this.state);
  }

  render() {
    const filterAddSelection = (
      <>
        <select
          class="filter-selection"
          onChange={(e) =>
            this.setState({ title: e.target.value, active: true })
          }
        >
          {this.props.availableFilters.map((i) => (
            <option value={i.title}>{i.display_title}</option>
          ))}
        </select>
        <FontAwesomeIcon
          icon={faCheck}
          onClick={() => this.sendFilterUpdate()}
        />
      </>
    );

    const makeHeader = (name, editable) => (
      <div className="filter-card--header">
        {editable ? filterAddSelection : <h4>{name}</h4>}
      </div>
    );

    return (
      <div className="filter-card">
        {makeHeader(this.props.name, this.props.editable)}
      </div>
    );
  }
}
