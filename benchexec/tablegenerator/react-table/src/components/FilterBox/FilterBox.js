import React from "react";
import FilterContainer from "./FilterContainer";

const linkDataToTool = (toolIdx, columns, data) => {
  const out = columns;
  //prepare columns
  for (const column of out) {
    column.data = [];
    column.distincts = {};
    column.min = Infinity;
    column.max = -Infinity;
  }
  for (const row of data) {
    const toolResult = row.results[toolIdx];
    for (const index in out) {
      const value = toolResult.values[index];
      let { min, max, type } = out[index];
      out[index].data.push(value);

      if (value.raw === undefined) {
        continue;
      }
      // aggregate data
      if (type === "status" || type === "text") {
        // using a plain object as a simple representation of a set
        out[index].distincts[value.raw] = true;
      } else {
        min = Number(min);
        max = Number(max);
        if (value.raw < min) {
          min = value.raw;
        }
        if (value.raw > max) {
          max = value.raw;
        }
        out[index].min = min;
        out[index].max = max;
      }
    }
  }

  // turning the distincts set into an array
  console.log(out);
  return out.map((col) => ({ ...col, distincts: Object.keys(col.distincts) }));
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
