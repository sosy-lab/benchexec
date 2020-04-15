/* SPDX-License-Identifier: Apache-2.0
 *
 * BenchExec is a framework for reliable benchmarking.
 * This file is part of BenchExec.
 * Copyright (C) Dirk Beyer. All rights reserved.
 */
import React from "react";
import "../../node_modules/react-vis/dist/style.css";
import {
  XYPlot,
  MarkSeries,
  VerticalGridLines,
  HorizontalGridLines,
  XAxis,
  YAxis,
  Hint,
  DecorativeAxis,
} from "react-vis";
import {
  getRunSetName,
  setParam,
  getHashSearch,
  isNil,
  stringAsBoolean,
} from "../utils/utils";

const defaultValues = {
  correct: "true",
  linear: "false",
  line: 10,
};

const getFirstVisible = (tool) =>
  tool.columns.find((column) => column.isVisible && column.type !== "status");
export default class ScatterPlot extends React.Component {
  constructor(props) {
    super(props);
    const defaultName =
      getRunSetName(this.props.tools[0]) + " " + this.props.columns[0][1];

    let { correct, linear, toolX, toolY, columnX, columnY, line } = {
      ...defaultValues,
      ...getHashSearch(),
    };

    correct = stringAsBoolean(correct);
    linear = stringAsBoolean(linear);

    let dataX;
    let dataY;

    if (isNil(toolX) || isNil(columnX)) {
      dataX = `0-${getFirstVisible(this.props.tools[0]).display_title}`;
    } else {
      dataX = `${toolX}-${columnX}`;
    }

    if (isNil(toolY) || isNil(columnY)) {
      dataY = `0-${getFirstVisible(this.props.tools[0]).display_title}`;
    } else {
      dataY = `${toolY}-${columnY}`;
    }

    this.state = {
      dataX,
      dataY,
      correct: typeof correct === "boolean" ? correct : true,
      linear: linear || false,
      toolX: 0,
      toolY: 0,
      line: line || 10,
      columnX: 1,
      columnY: 1,
      nameX: defaultName,
      nameY: defaultName,
      value: false,
      width: window.innerWidth,
      height: window.innerHeight,
    };

    if (dataX) {
      this.state = { ...this.state, ...this.extractAxisInfoByName(dataX, "X") };
    }
    if (dataY) {
      this.state = { ...this.state, ...this.extractAxisInfoByName(dataY, "Y") };
    }

    this.lineValues = [
      2,
      3,
      4,
      5,
      6,
      7,
      8,
      9,
      10,
      100,
      1000,
      10000,
      100000,
      1000000,
      10000000,
      100000000,
    ];
    this.maxX = "";
    this.minX = "";
    this.lineCount = 1;
  }

  // ----------------------resizer-------------------------------
  componentDidMount() {
    window.addEventListener("resize", this.updateDimensions);
  }

  componentWillUnmount() {
    window.removeEventListener("resize", this.updateDimensions);
  }

  updateDimensions = () => {
    this.setState({
      width: window.innerWidth,
      height: window.innerHeight,
    });
  };

  // --------------------rendering-----------------------------
  renderColumns = () => {
    return this.props.tools.map((runset, i) => (
      <optgroup key={"runset" + i} label={getRunSetName(runset)}>
        {runset.columns.map((column, j) => {
          return column.isVisible ? (
            <option
              key={i + column.display_title}
              value={i + "-" + column.display_title.replace("-", "___")}
              name={column.display_title}
            >
              {column.display_title}
            </option>
          ) : null;
        })}
      </optgroup>
    ));
  };

  renderData = () => {
    let array = [];
    this.hasInvalidLog = false;

    this.props.table.forEach((row) => {
      const resX = row.results[this.state.toolX];
      const resY = row.results[this.state.toolY];
      const x = resX.values[this.state.columnX].raw;
      const y = resY.values[this.state.columnY].raw;
      const hasValues =
        x !== undefined && x !== null && y !== undefined && y !== null;

      if (
        hasValues &&
        (!this.state.correct ||
          (this.state.correct &&
            resX.category === "correct" &&
            resY.category === "correct"))
      ) {
        const isLogAndInvalid = !this.state.linear && (x <= 0 || y <= 0);

        if (isLogAndInvalid) {
          this.hasInvalidLog = true;
        } else {
          array.push({
            x,
            y,
            info: this.props.getRowName(row),
          });
        }
      }
    });

    this.setMinMaxValues(array);

    this.lineCount = array.length;
    this.dataArray = array;
  };

  setMinMaxValues = (array) => {
    const xValues = array.map((el) => el.x);
    const yValues = array.map((el) => el.y);

    this.maxX = this.findMaxValue(xValues);
    this.maxY = this.findMaxValue(yValues);
    this.minX = this.findMinValue(xValues);
    this.minY = this.findMinValue(yValues);
  };

  findMaxValue = (values) => {
    const max = Math.max(...values);
    return max < 3 ? 3 : max;
  };

  findMinValue = (values) => {
    const min = Math.min(...values);
    return min > 2 ? 1 : min;
  };

  // ------------------------handeling----------------------------
  handleType = (tool, column) => {
    if (
      this.props.tools[tool].columns[column].type === "text" ||
      this.props.tools[tool].columns[column].type === "status"
    ) {
      return "ordinal";
    } else {
      return this.state.linear ? "linear" : "log";
    }
  };
  toggleCorrectResults = () => {
    setParam({ correct: !this.state.correct });
    this.setState((prevState) => ({
      correct: !prevState.correct,
    }));
  };
  toggleLinear = () => {
    setParam({ linear: !this.state.linear });
    this.setState((prevState) => ({
      linear: !prevState.linear,
    }));
  };

  extractAxisInfoByName = (val, axis) => {
    let [toolIndex, columnName] = val.split("-");
    columnName = columnName.replace("___", "-");
    return {
      [`data${axis}`]: val,
      [`tool${axis}`]: toolIndex,
      [`column${axis}`]: this.props.tools[toolIndex].columns.findIndex(
        (item) => item.display_title === columnName,
      ),
      [`name${axis}`]: columnName,
    };
  };
  handleAxis = (ev, axis) => {
    this.array = [];
    let [tool, column] = ev.target.value.split("-");
    column = column.replace("___", "-");
    setParam({ [`tool${axis}`]: tool, [`column${axis}`]: column });
    this.setState(this.extractAxisInfoByName(ev.target.value, axis));
  };
  handleLine = ({ target }) => {
    setParam({ line: target.value });
    this.setState({
      line: target.value,
    });
  };

  render() {
    this.renderData();
    return (
      <div className="scatterPlot">
        <div className="scatterPlot__select">
          <span> X: </span>
          <select
            name="Value XAxis"
            value={this.state.dataX}
            onChange={(ev) => this.handleAxis(ev, "X")}
          >
            {this.renderColumns()}
          </select>
          <span> Y: </span>
          <select
            name="Value YAxis"
            value={this.state.dataY}
            onChange={(ev) => this.handleAxis(ev, "Y")}
          >
            {this.renderColumns()}
          </select>
          <span>Line:</span>
          <select
            name="Line"
            value={this.state.line}
            onChange={this.handleLine}
          >
            {this.lineValues.map((value) => {
              return (
                <option key={value} name={value} value={value}>
                  {value}
                </option>
              );
            })}
          </select>
        </div>
        <XYPlot
          className="scatterPlot__plot"
          height={this.state.height - 200}
          width={this.state.width - 100}
          margin={{ left: 90 }}
          yType={this.handleType(this.state.toolY, this.state.columnY)}
          xType={this.handleType(this.state.toolX, this.state.columnX)}
          xDomain={
            this.handleType(this.state.toolX, this.state.columnX) !== "ordinal"
              ? [this.minX, this.maxX]
              : null
          }
          yDomain={
            this.handleType(this.state.toolY, this.state.columnY) !== "ordinal"
              ? [this.minY, this.maxY]
              : null
          }
        >
          <VerticalGridLines
            yType={this.handleType(this.state.toolY, this.state.columnY)}
            xType={this.handleType(this.state.toolX, this.state.columnX)}
          />
          <HorizontalGridLines
            yType={this.handleType(this.state.toolY, this.state.columnY)}
            xType={this.handleType(this.state.toolX, this.state.columnX)}
          />

          <DecorativeAxis
            className="middle-line"
            axisStart={{
              x: this.state.linear ? 0 : 1,
              y: this.state.linear ? 0 : 1,
            }}
            axisEnd={{
              x: this.maxX > this.maxY ? this.maxX : this.maxY,
              y: this.maxX > this.maxY ? this.maxX : this.maxY,
            }}
            axisDomain={[0, 10000000000]}
            style={{
              ticks: { stroke: "#009440", opacity: 0 },
              text: {
                stroke: "none",
                fill: "#009440",
                fontWeight: 600,
                opacity: 0,
              },
            }}
          />
          <DecorativeAxis
            axisStart={{
              x: this.state.linear ? 0 : this.state.line,
              y: this.state.linear ? 0 : 1,
            }}
            axisEnd={{ x: this.maxX, y: this.maxX / this.state.line }}
            axisDomain={[0, 10000000000]}
            style={{
              ticks: { stroke: "#ADDDE1", opacity: 0 },
              text: {
                stroke: "none",
                fill: "#6b6b76",
                fontWeight: 600,
                opacity: 0,
              },
            }}
          />
          <DecorativeAxis
            axisStart={{
              x: this.state.linear ? 0 : 1,
              y: this.state.linear ? 0 : this.state.line,
            }}
            axisEnd={{ x: this.maxX, y: this.maxX * this.state.line }}
            axisDomain={[0, 10000000000]}
            style={{
              ticks: { stroke: "#ADDDE1", opacity: 0 },
              text: {
                stroke: "none",
                fill: "#6b6b76",
                fontWeight: 600,
                opacity: 0,
              },
            }}
          />
          <XAxis
            title={this.state.nameX}
            tickFormat={(value) => value}
            yType={this.handleType(this.state.toolY, this.state.columnY)}
            xType={this.handleType(this.state.toolX, this.state.columnX)}
          />
          <YAxis
            title={this.state.nameY}
            tickFormat={(value) => value}
            yType={this.handleType(this.state.toolY, this.state.columnY)}
            xType={this.handleType(this.state.toolX, this.state.columnX)}
          />
          <MarkSeries
            data={this.dataArray}
            onValueMouseOver={(datapoint, event) =>
              this.setState({ value: datapoint })
            }
            onValueMouseOut={(datapoint, event) =>
              this.setState({ value: null })
            }
          />
          {this.state.value ? <Hint value={this.state.value} /> : null}
        </XYPlot>
        {this.lineCount === 0 && (
          <div className="plot__noresults">
            No {this.state.correct && "correct"} results
            {this.props.table.length > 0 && " with valid data points"}
            {this.hasInvalidLog &&
              " (negative values are not shown in logarithmic plot)"}
          </div>
        )}
        <button className="btn" onClick={this.toggleLinear}>
          {this.state.linear
            ? "Switch to Logarithmic Scale"
            : "Switch to Linear Scale"}
        </button>
        <button className="btn" onClick={this.toggleCorrectResults}>
          {this.state.correct
            ? "Switch to All Results"
            : "Switch to Correct Results Only"}
        </button>
      </div>
    );
  }
}
