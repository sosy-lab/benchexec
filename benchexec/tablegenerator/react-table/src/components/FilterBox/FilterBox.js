import React from "react";
import FilterContainer from "./FilterContainer";

const linkDataToTool = (toolIdx, columns, data) => {
  const out = columns;
  for (const row of data) {
    const toolResult = row.results[toolIdx];
    for (const index in out) {
      if (!out[index].data) {
        out[index].data = [];
      }
      out[index].data.push(toolResult.values[index]);
    }
  }
  return out;
};

const extractFilterValues = (columns) => {
  const out = {};
  for (const column of columns) {
    out[column.title] = { ...column, filtered: false, value: null };
  }
  return out;
};

export default class FilterBox extends React.Component {
  constructor(props) {
    super(props);
    console.log(props);

    const { tools, data } = props;

    const preppedTools = tools.map(
      ({ niceName, date, tool, isVisible, columns }, idx) => ({
        name: `${tool} ${date} ${niceName}`,
        isVisible,
        columns: linkDataToTool(idx, columns, data),
        filters: extractFilterValues(columns),
        index: idx,
      }),
    );

    this.state = {
      preppedTools,
    };

    console.log(this.state);
  }
  render() {
    return (
      <div className="filterBox">
        {this.state.preppedTools.map((tool) => {
          return (
            <FilterContainer toolName={tool.name} filters={tool.columns} />
          );
        })}
      </div>
    );
  }
}
