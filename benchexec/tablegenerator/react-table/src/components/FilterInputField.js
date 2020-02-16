import React from "react";

export default class FilterInputField extends React.Component {
  constructor(props) {
    super(props);
    this.elementId = `${props.column.id}_filter`;
    this.filter = props.filter ? props.filter.value : props.filter;
  }

  numericPattern = "([+-]?[0-9]*(\\.[0-9]*)?)(:[+-]?[0-9]*(\\.[0-9]*)?)?";

  onChange = event => {
    this.value = event.target.value;
    clearTimeout(this.typingTimer);
    this.typingTimer = setTimeout(() => {
      this.props.onChange(this.value);
      document.getElementById(this.elementId).focus();
    }, 500);
  };

  render = () => (
    <input
      id={this.elementId}
      placeholder={this.props.numeric ? "Min:Max" : "text"}
      defaultValue={this.value ? this.value : this.filter}
      onChange={this.onChange}
      type="search"
      pattern={this.props.numeric ? this.numericPattern : undefined}
    />
  );
}
