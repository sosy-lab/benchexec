import React from "react";
import FilterContainer from "./FilterContainer";
import { faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";

export default class FilterBox extends React.Component {
  constructor(props) {
    super(props);
    console.log(props);

    const { filterable, filtered } = props;

    this.state = {
      filterable,
      filters: this.createFiltersFromReactTableStructure(filtered),
    };
  }

  componentDidUpdate(prevProps) {
    if (prevProps.filtered !== this.props.filtered) {
      this.setState({
        filters: this.createFiltersFromReactTableStructure(this.props.filtered),
      });
    }
    console.log(this.state);
  }

  createFiltersFromReactTableStructure(filters) {
    if (!filters || !filters.length) {
      return [];
    }

    console.log({ filters });

    const out = [];

    for (const { id, value } of filters.flat()) {
      const [tool, title, col] = id.split("_");
      const toolArr = out[tool] || [];
      if (!toolArr[col]) {
        toolArr[col] = { title, values: [value] };
      } else {
        toolArr[col].values.push(value);
      }
      out[tool] = toolArr;
    }

    return out;
  }

  flattenFilterStructure() {
    return Object.values(Object.values(this.state.filters));
  }

  sendFilters(filter) {
    const filters = filter.filter((i) => i !== null && i !== undefined);

    console.log({ filters });

    this.props.setFilter(
      filters
        .map((tool, toolIdx) => {
          return tool.map((col, colIdx) => {
            return col.values.map((val) => ({
              id: `${toolIdx}_${col.title}_${colIdx}`,
              value: val,
            }));
          });
        })
        .flat(3)
        .filter((i) => i !== null && i !== undefined),
      true,
    );
  }

  updateFilters(toolIdx, columnIdx, data) {
    console.log({ toolIdx, columnIdx, data });
    //this.props.setFilter(newFilter);
    const newFilters = [...this.state.filters];
    newFilters[toolIdx] = newFilters[toolIdx] || [];
    newFilters[toolIdx][columnIdx] = data;
    this.setState({ filters: newFilters });
    console.log(this.state.filters);
    this.sendFilters(newFilters);
  }

  render() {
    return (
      <div
        className={`filterBox ${this.props.visible ? "" : "filterBox--hidden"}`}
      >
        <div className="filterBox--header">
          <FontAwesomeIcon
            icon={faTimes}
            className="filterBox--header--icon"
            onClick={this.props.hide}
          />
          {this.props.headerComponent}
        </div>
        {this.state.filterable.map((tool, idx) => {
          return (
            <FilterContainer
              updateFilters={(data, columnIndex) =>
                this.updateFilters(idx, columnIndex, data)
              }
              currentFilters={this.state.filters[idx] || []}
              toolName={tool.name}
              filters={tool.columns}
              key={`filtercontainer-${idx}`}
            />
          );
        })}
      </div>
    );
  }
}
