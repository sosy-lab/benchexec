// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import React from "react";
import "../../node_modules/react-vis/dist/style.css";
import {
  MarkSeries,
  VerticalGridLines,
  HorizontalGridLines,
  XAxis,
  YAxis,
  Hint,
  DecorativeAxis,
  XYPlot,
  FlexibleXYPlot,
} from "react-vis";
import {
  getRunSetName,
  setParam,
  getHashSearch,
  isNil,
  getFirstVisibles,
} from "../utils/utils";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faExchangeAlt } from "@fortawesome/free-solid-svg-icons";
import { renderSetting, renderOptgroupsSetting } from "../utils/plot";

const scalingOptions = {
  linear: "Linear",
  logarithmic: "Logarithmic",
};

const resultsOptions = {
  all: "All",
  correct: "Correct only",
};

const lineOptgroupOptions = {
  "f(x) = cx and f(x) = x/c": [
    { name: "c = 1.1", value: 1.1 },
    { name: "c = 1.2", value: 1.2 },
    { name: "c = 1.5", value: 1.5 },
    { name: "c = 2", value: 2 },
    { name: "c = 3", value: 3 },
    { name: "c = 4", value: 4 },
    { name: "c = 5", value: 5 },
    { name: "c = 6", value: 6 },
    { name: "c = 7", value: 7 },
    { name: "c = 8", value: 8 },
    { name: "c = 9", value: 9 },
    { name: "c = 10", value: 10 },
    { name: "c = 100", value: 100 },
    { name: "c = 1000", value: 1000 },
    { name: "c = 10000", value: 10000 },
    { name: "c = 100000", value: 100000 },
    { name: "c = 1000000", value: 1000000 },
  ],
};

const defaultValues = {
  scaling: scalingOptions.logarithmic,
  results: resultsOptions.correct,
  line: Object.values(lineOptgroupOptions)[0][11].value,
};

export default class ScatterPlot extends React.Component {
  constructor(props) {
    super(props);

    this.state = this.setup();
    this.maxX = "";
    this.minX = "";
    this.lineCount = 1;
  }

  setup() {
    const defaultName =
      getRunSetName(this.props.tools[0]) + " " + this.props.columns[0][1];

    let { results, scaling, toolX, toolY, columnX, columnY, line } = {
      ...defaultValues,
      ...getHashSearch(),
    };

    let dataX, dataY, areAllColsHidden;

    if (isNil(toolX) || isNil(columnX)) {
      const [firstVisibleTool, firstVisibleColumn] = getFirstVisibles(
        this.props.tools,
        this.props.hiddenCols,
      );
      areAllColsHidden = firstVisibleTool === undefined;
      toolX = firstVisibleTool;
      dataX = `${firstVisibleTool}-${firstVisibleColumn}`;
    } else {
      areAllColsHidden = false;
      dataX = `${toolX}-${columnX}`;
    }

    if (isNil(toolY) || isNil(columnY)) {
      const [firstVisibleTool, firstVisibleColumn] = getFirstVisibles(
        this.props.tools,
        this.props.hiddenCols,
      );
      areAllColsHidden = firstVisibleTool === undefined;
      toolY = firstVisibleTool;
      dataY = `${firstVisibleTool}-${firstVisibleColumn}`;
    } else {
      areAllColsHidden = false;
      dataY = `${toolY}-${columnY}`;
    }

    let out = {
      dataX,
      dataY,
      results,
      scaling,
      toolX: 0,
      toolY: 0,
      line,
      columnX: 1,
      columnY: 1,
      nameX: defaultName,
      nameY: defaultName,
      value: false,
      areAllColsHidden,
    };

    if (dataX && !areAllColsHidden) {
      out = { ...out, ...this.extractAxisInfoByName(dataX, "X") };
    }
    if (dataY && !areAllColsHidden) {
      out = { ...out, ...this.extractAxisInfoByName(dataY, "Y") };
    }
    return out;
  }

  // ----------------------resizer-------------------------------
  componentDidMount() {
    window.addEventListener("popstate", this.refreshUrlState);
  }

  componentWillUnmount() {
    window.removeEventListener("popstate", this.refreshUrlState);
  }

  refreshUrlState = () => {
    this.setState(this.setup());
  };

  // --------------------rendering-----------------------------
  renderData = () => {
    let array = [];
    this.hasInvalidLog = false;

    if (!this.state.areAllColsHidden) {
      this.props.table.forEach((row) => {
        const resX = row.results[this.state.toolX];
        const resY = row.results[this.state.toolY];
        const x = resX.values[this.state.columnX].raw;
        const y = resY.values[this.state.columnY].raw;
        const hasValues =
          x !== undefined && x !== null && y !== undefined && y !== null;
        const areOnlyCorrectResults =
          this.state.results === resultsOptions.correct;

        if (
          hasValues &&
          (!areOnlyCorrectResults ||
            (areOnlyCorrectResults &&
              resX.category === "correct" &&
              resY.category === "correct"))
        ) {
          const isLogAndInvalid =
            this.state.scaling === scalingOptions.logarithmic &&
            (x <= 0 || y <= 0);

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
    }

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

  renderAllSettings() {
    const axisOptions = this.props.tools.reduce(
      (acc, runset, runsetIdx) =>
        Object.assign(acc, {
          [getRunSetName(runset)]: runset.columns
            .filter(
              (col) => !this.props.hiddenCols[runsetIdx].includes(col.colIdx),
            )
            .map((col, j) => ({
              name: col.display_title,
              value: runsetIdx + "-" + col.colIdx,
            })),
        }),
      {},
    );
    return (
      <div className="settings-container">
        <div className="settings-border-container">
          <div className="settings-subcontainer flexible-width">
            {renderOptgroupsSetting(
              "X-Axis",
              this.state.dataX,
              (ev) => this.setAxis(ev, "X"),
              axisOptions,
            )}
            <span className="setting icon">
              <FontAwesomeIcon
                icon={faExchangeAlt}
                onClick={() => this.swapAxes()}
              />
            </span>
            {renderOptgroupsSetting(
              "Y-Axis",
              this.state.dataY,
              (ev) => this.setAxis(ev, "Y"),
              axisOptions,
            )}
          </div>
          <div className="settings-subcontainer">
            {renderSetting(
              "Scaling",
              this.state.scaling,
              (ev) => setParam({ scaling: ev.target.value }),
              scalingOptions,
            )}
            {renderSetting(
              "Results",
              this.state.results,
              (ev) => setParam({ results: ev.target.value }),
              resultsOptions,
              "In addition to which results are selected here, any filters will still be applied.",
            )}
            <div className="settings-subcontainer">
              {renderOptgroupsSetting(
                "Aux. Lines",
                this.state.line,
                (ev) => setParam({ line: ev.target.value }),
                lineOptgroupOptions,
                "Adds the two auxiliary lines f(x) = cx and f(x) = x/c to the plot, with c being the chosen factor in the dropdown.",
              )}
            </div>
          </div>
        </div>
      </div>
    );
  }

  // ------------------------handeling----------------------------
  handleType = (tool, column) => {
    const colType = this.props.tools[tool].columns[column].type;
    if (colType === "text" || colType === "status") {
      return "ordinal";
    } else {
      return this.state.scaling === scalingOptions.logarithmic
        ? "log"
        : "linear";
    }
  };

  extractAxisInfoByName = (val, axis) => {
    let [toolIndex, colIdx] = val.split("-");
    return {
      [`data${axis}`]: val,
      [`tool${axis}`]: toolIndex,
      [`column${axis}`]: colIdx,
      [`name${axis}`]:
        this.props.tools[toolIndex].columns.find(
          (col) => col.colIdx === parseInt(colIdx),
        ).display_title +
        " (" +
        getRunSetName(this.props.tools[toolIndex]) +
        ")",
    };
  };

  setAxis = (ev, axis) => {
    this.array = [];
    let [tool, column] = ev.target.value.split("-");
    column = column.replace("___", "-");
    setParam({ [`tool${axis}`]: tool, [`column${axis}`]: column });
  };

  swapAxes = () => {
    this.array = [];
    setParam({
      toolX: this.state.toolY,
      toolY: this.state.toolX,
      columnX: this.state.columnY,
      columnY: this.state.columnX,
    });
  };

  render() {
    this.renderData();
    const isLinear = this.state.scaling === scalingOptions.linear;
    const Plot = this.props.isFlexible ? FlexibleXYPlot : XYPlot;
    const plotDimensions = this.props.isFlexible
      ? {
          height: window.innerHeight - 200,
        }
      : {
          height: 1000,
          width: 1500,
        };
    return (
      <div className="scatterPlot">
        {!this.state.areAllColsHidden && this.renderAllSettings()}
        <Plot
          className="scatterPlot__plot"
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
          {...plotDimensions}
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
              x: isLinear ? 0 : 1,
              y: isLinear ? 0 : 1,
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
              x: isLinear ? 0 : this.state.line,
              y: isLinear ? 0 : 1,
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
              x: isLinear ? 0 : 1,
              y: isLinear ? 0 : this.state.line,
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
        </Plot>
        {this.state.areAllColsHidden ? (
          <div className="plot__noresults">No columns to show!</div>
        ) : (
          this.lineCount === 0 && (
            <div className="plot__noresults">
              No {this.state.results === resultsOptions.correct && "correct"}{" "}
              results
              {this.props.table.length > 0 && " with valid data points"}
              {this.hasInvalidLog &&
                " (negative values are not shown in logarithmic plot)"}
            </div>
          )
        )}
      </div>
    );
  }
}
