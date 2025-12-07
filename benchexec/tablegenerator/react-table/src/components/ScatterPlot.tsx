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
  LineSeries,
  LineMarkSeries,
} from "react-vis";
import {
  getRunSetName,
  setURLParameter,
  getURLParameters,
  isNil,
  getFirstVisibles,
} from "../utils/utils";
import {
  renderSetting,
  renderOptgroupsSetting,
  getConfidenceIntervalBorders,
  getDataPointsOfRegression,
  renderResetButton,
} from "../utils/plot";
// @ts-expect-error TS(7016): Could not find a declaration file for module 'regr... Remove this comment to see the full error message
import calcRegression from "regression";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faExchangeAlt } from "@fortawesome/free-solid-svg-icons";

export default class ScatterPlot extends React.Component {
  array: any;
  dataArray: any;
  defaultValues: any;
  hasInvalidLog: any;
  lineCount: any;
  lineOptgroupOptions: any;
  maxX: any;
  maxY: any;
  minX: any;
  minY: any;
  regressionData: any;
  regressionOptions: any;
  resultsOptions: any;
  scalingOptions: any;
  constructor(props: any) {
    super(props);

    this.scalingOptions = {
      linear: "Linear",
      logarithmic: "Logarithmic",
    };

    this.resultsOptions = {
      all: "All",
      correct: "Correct only",
    };

    this.regressionOptions = {
      none: "None",
      linear: "Linear",
    };

    this.lineOptgroupOptions = {
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

    this.defaultValues = {
      scaling: this.scalingOptions.logarithmic,
      results: this.resultsOptions.correct,
      regression: this.regressionOptions.none,
      // @ts-expect-error TS(2571): Object is of type 'unknown'.
      line: Object.values(this.lineOptgroupOptions)[0][11].value,
    };

    this.state = this.setup();
    this.maxX = "";
    this.minX = "";
    this.lineCount = 1;
  }

  setup() {
    const defaultName =
      // @ts-expect-error TS(2339): Property 'tools' does not exist on type 'Readonly<... Remove this comment to see the full error message
      getRunSetName(this.props.tools[0]) + " " + this.props.columns[0][1];

    let {
      results,
      scaling,
      toolX,
      toolY,
      columnX,
      columnY,
      line,
      regression,
    }: any = {
      ...this.defaultValues,
      // @ts-expect-error TS(2554): Expected 1 arguments, but got 0.
      ...getURLParameters(),
    };

    let dataX, dataY, areAllColsHidden;

    if (isNil(toolX) || isNil(columnX)) {
      const [firstVisibleTool, firstVisibleColumn] = getFirstVisibles(
        // @ts-expect-error TS(2339): Property 'tools' does not exist on type 'Readonly<... Remove this comment to see the full error message
        this.props.tools,
        // @ts-expect-error TS(2339): Property 'hiddenCols' does not exist on type 'Read... Remove this comment to see the full error message
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
        // @ts-expect-error TS(2339): Property 'tools' does not exist on type 'Readonly<... Remove this comment to see the full error message
        this.props.tools,
        // @ts-expect-error TS(2339): Property 'hiddenCols' does not exist on type 'Read... Remove this comment to see the full error message
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
      regression,
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

  checkForNumericalSelections = () =>
    // @ts-expect-error TS(2339): Property 'toolY' does not exist on type 'Readonly<... Remove this comment to see the full error message
    this.handleType(this.state.toolY, this.state.columnY) !== "ordinal" &&
    // @ts-expect-error TS(2339): Property 'toolX' does not exist on type 'Readonly<... Remove this comment to see the full error message
    this.handleType(this.state.toolX, this.state.columnX) !== "ordinal";

  // --------------------rendering-----------------------------
  renderData = () => {
    let array: any = [];
    this.hasInvalidLog = false;

    // @ts-expect-error TS(2339): Property 'areAllColsHidden' does not exist on type... Remove this comment to see the full error message
    if (!this.state.areAllColsHidden) {
      // @ts-expect-error TS(2339): Property 'table' does not exist on type 'Readonly<... Remove this comment to see the full error message
      this.props.table.forEach((row: any) => {
        // @ts-expect-error TS(2339): Property 'toolX' does not exist on type 'Readonly<... Remove this comment to see the full error message
        const resX = row.results[this.state.toolX];
        // @ts-expect-error TS(2339): Property 'toolY' does not exist on type 'Readonly<... Remove this comment to see the full error message
        const resY = row.results[this.state.toolY];
        // @ts-expect-error TS(2339): Property 'columnX' does not exist on type 'Readonl... Remove this comment to see the full error message
        const x = resX.values[this.state.columnX].raw;
        // @ts-expect-error TS(2339): Property 'columnY' does not exist on type 'Readonl... Remove this comment to see the full error message
        const y = resY.values[this.state.columnY].raw;
        const hasValues =
          x !== undefined && x !== null && y !== undefined && y !== null;
        const areOnlyCorrectResults =
          // @ts-expect-error TS(2339): Property 'results' does not exist on type 'Readonl... Remove this comment to see the full error message
          this.state.results === this.resultsOptions.correct;

        if (
          hasValues &&
          (!areOnlyCorrectResults ||
            (areOnlyCorrectResults &&
              resX.category === "correct" &&
              resY.category === "correct"))
        ) {
          const isLogAndInvalid =
            // @ts-expect-error TS(2339): Property 'scaling' does not exist on type 'Readonl... Remove this comment to see the full error message
            this.state.scaling === this.scalingOptions.logarithmic &&
            (x <= 0 || y <= 0);

          if (isLogAndInvalid) {
            this.hasInvalidLog = true;
          } else {
            array.push({
              x: x,
              y: y,
              // @ts-expect-error TS(2339): Property 'getRowName' does not exist on type 'Read... Remove this comment to see the full error message
              info: this.props.getRowName(row),
            });
          }
        }
      });
    }

    this.setMinMaxValues(array);
    this.lineCount = array.length;
    this.dataArray = array;

    const isRegressionEnabled =
      // @ts-expect-error TS(2339): Property 'regression' does not exist on type 'Read... Remove this comment to see the full error message
      this.state.regression !== this.regressionOptions.none;
    const areSelectionsNumerical = this.checkForNumericalSelections();
    if (isRegressionEnabled) {
      if (this.lineCount === 0 || !areSelectionsNumerical) {
        setURLParameter({ regression: this.regressionOptions.none });
      } else {
        // @ts-expect-error TS(7006): Parameter 'data' implicitly has an 'any' type.
        const regressionDataArray = array.map((data) => [
          parseFloat(data.x),
          parseFloat(data.y),
        ]);
        const regression = calcRegression.linear(regressionDataArray);
        const confidenceIntervalBorders = getConfidenceIntervalBorders(
          regressionDataArray,
          regression.points,
          regression.predict,
          this.minX,
          this.maxX,
        );
        /* Due to points with same x but different y value, there may be many duplicates in the regression data. Those can be used for
           easier calculation for the 95% Confidence Intervals, but aren't necessary afterwards since they'll only be used to draw the line.
           To have a line from the start to the end of the coordinate system, the points at the borders are added here too. */
        const endPoints = [
          [this.minX, regression.predict(this.minX)[1]],
          [this.maxX, regression.predict(this.maxX)[1]],
        ];
        regression.points = Array.from(
          // @ts-expect-error TS(2769): No overload matches this call.
          new Set(regression.points.map(JSON.stringify)),
          JSON.parse,
        ).concat(endPoints);

        const unitX =
          // @ts-expect-error TS(2339): Property 'tools' does not exist on type 'Readonly<... Remove this comment to see the full error message
          this.props.tools[this.state.toolX].columns[this.state.columnX].unit;
        const unitY =
          // @ts-expect-error TS(2339): Property 'tools' does not exist on type 'Readonly<... Remove this comment to see the full error message
          this.props.tools[this.state.toolY].columns[this.state.columnY].unit;
        const helpText = `Estimation technique: ordinary least squares (OLS)
                          // @ts-expect-error TS(2339): Property 'nameX' does not exist on type 'Readonly<... Remove this comment to see the full error message
                          Predictor variable (X-Axis) in ${unitX}: ${this.state.nameX}
                          // @ts-expect-error TS(2339): Property 'nameY' does not exist on type 'Readonly<... Remove this comment to see the full error message
                          Response variable (Y-Axis) in ${unitY}: ${this.state.nameY}
                          Regression coefficient: ${regression.equation[0]}
                          Intercept: ${regression.equation[1]}
                          Equation: ${regression.string}
                          Coefficient of Determination: ${regression.r2}`.replace(
          /^ +/gm,
          "",
        );
        this.regressionData = {
          regression,
          text: helpText,
          upperConfidenceBorderData: confidenceIntervalBorders.upperBorderData,
          lowerConfidenceBorderData: confidenceIntervalBorders.lowerBorderData,
        };
      }
    }
  };

  setMinMaxValues = (array: any) => {
    const xValues = array.map((el: any) => el.x);
    const yValues = array.map((el: any) => el.y);

    this.maxX = this.findMaxValue(xValues);
    this.maxY = this.findMaxValue(yValues);
    this.minX = this.findMinValue(xValues);
    this.minY = this.findMinValue(yValues);
  };

  findMaxValue = (values: any) => {
    const max = Math.max(...values);
    return max < 3 ? 3 : max;
  };

  findMinValue = (values: any) => {
    const min = Math.min(...values);
    return min > 2 ? 1 : min;
  };

  renderAllSettings() {
    // @ts-expect-error TS(2339): Property 'tools' does not exist on type 'Readonly<... Remove this comment to see the full error message
    const axisOptions = this.props.tools.reduce(
      (acc: any, runset: any, runsetIdx: any) =>
        Object.assign(acc, {
          [getRunSetName(runset)]: runset.columns
            .filter(
              (col: any) =>
                // @ts-expect-error TS(2339): Property 'hiddenCols' does not exist on type 'Read... Remove this comment to see the full error message
                !this.props.hiddenCols[runsetIdx].includes(col.colIdx),
            )
            // @ts-expect-error TS(7006): Parameter 'col' implicitly has an 'any' type.
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
            // @ts-expect-error TS(2554): Expected 5 arguments, but got 4.
            {renderOptgroupsSetting(
              "X-Axis",
              // @ts-expect-error TS(2339): Property 'dataX' does not exist on type 'Readonly<... Remove this comment to see the full error message
              this.state.dataX,
              (ev: any) => this.setAxis(ev, "X"),
              axisOptions,
            )}
            <span className="setting icon">
              <FontAwesomeIcon
                icon={faExchangeAlt}
                onClick={() => this.swapAxes()}
              />
            </span>
            // @ts-expect-error TS(2554): Expected 5 arguments, but got 4.
            {renderOptgroupsSetting(
              "Y-Axis",
              // @ts-expect-error TS(2339): Property 'dataY' does not exist on type 'Readonly<... Remove this comment to see the full error message
              this.state.dataY,
              (ev: any) => this.setAxis(ev, "Y"),
              axisOptions,
            )}
          </div>
          <div className="settings-subcontainer">
            // @ts-expect-error TS(2554): Expected 6 arguments, but got 4.
            {renderSetting(
              "Scaling",
              // @ts-expect-error TS(2339): Property 'scaling' does not exist on type 'Readonl... Remove this comment to see the full error message
              this.state.scaling,
              (ev: any) => setURLParameter({ scaling: ev.target.value }),
              this.scalingOptions,
            )}
            // @ts-expect-error TS(2554): Expected 6 arguments, but got 5.
            {renderSetting(
              "Results",
              // @ts-expect-error TS(2339): Property 'results' does not exist on type 'Readonl... Remove this comment to see the full error message
              this.state.results,
              (ev: any) => setURLParameter({ results: ev.target.value }),
              this.resultsOptions,
              "In addition to which results are selected here, any filters will still be applied.",
            )}
            <div className="settings-subcontainer">
              {renderOptgroupsSetting(
                "Aux. Lines",
                // @ts-expect-error TS(2339): Property 'line' does not exist on type 'Readonly<{... Remove this comment to see the full error message
                this.state.line,
                (ev: any) => setURLParameter({ line: ev.target.value }),
                this.lineOptgroupOptions,
                "Adds the two auxiliary lines f(x) = cx and f(x) = x/c to the plot, with c being the chosen factor in the dropdown.",
              )}
            </div>
          </div>
          <div className="settings-subcontainer">
            // @ts-expect-error TS(2554): Expected 6 arguments, but got 5.
            {renderSetting(
              "Regression",
              // @ts-expect-error TS(2339): Property 'regression' does not exist on type 'Read... Remove this comment to see the full error message
              this.state.regression,
              (ev: any) => {
                if (this.checkForNumericalSelections()) {
                  setURLParameter({ regression: ev.target.value });
                } else {
                  alert(
                    "Regressions are only available for numerical selections.",
                  );
                }
              },
              this.regressionOptions,
              // @ts-expect-error TS(2339): Property 'regression' does not exist on type 'Read... Remove this comment to see the full error message
              this.state.regression !== this.regressionOptions.none &&
                this.regressionData
                ? this.regressionData.text
                : undefined,
            )}
            {renderResetButton(() =>
              setURLParameter({
                columnX: null,
                columnY: null,
                line: null,
                regression: null,
                results: null,
                scaling: null,
                toolX: null,
                toolY: null,
              }),
            )}
          </div>
        </div>
      </div>
    );
  }

  renderRegressionAndConfidenceIntervals() {
    const minX = Math.floor(this.minX);
    const maxX = Math.ceil(this.maxX);
    const dataPointsOfRegression = getDataPointsOfRegression(
      minX,
      maxX,
      this.regressionData.regression.predict,
    );
    return [
      this.renderConfidenceIntervalLine(
        this.regressionData.upperConfidenceBorderData,
        "upper",
      ),
      this.renderConfidenceIntervalLine(
        this.regressionData.lowerConfidenceBorderData,
        "lower",
      ),
      this.renderRegressionLine(dataPointsOfRegression),
    ];
  }

  renderRegressionLine = (dataPoints: any) => {
    const lineData = this.prepareRegressionLineData(dataPoints);
    return (
      <LineMarkSeries
        className="regression-line"
        data={lineData}
        style={{
          stroke: "green",
        }}
        key={"reg-line-" + dataPoints}
        // @ts-expect-error TS(6133): 'event' is declared but its value is never read.
        onValueMouseOver={(datapoint, event) =>
          this.setState({ value: datapoint })
        }
        // @ts-expect-error TS(6133): 'datapoint' is declared but its value is never rea... Remove this comment to see the full error message
        onValueMouseOut={(datapoint, event) => this.setState({ value: null })}
        // @ts-expect-error TS(2769): No overload matches this call.
        opacity="0"
      />
    );
  };

  renderConfidenceIntervalLine = (dataPoints: any, identifier: any) => {
    const lineData = this.prepareLineData(dataPoints);
    return (
      <LineSeries
        className="regression-line"
        data={lineData}
        style={{
          stroke: "gray",
        }}
        key={`conf-line-${identifier}-${dataPoints}`}
      />
    );
  };

  prepareRegressionLineData = (dataPoints: any) =>
    dataPoints
      .sort((val1: any, val2: any) => val1[0] - val2[0])
      .map((data: any, index: any) => {
        const lowerBorderData =
          Math.round(
            this.regressionData.lowerConfidenceBorderData[index][1] * 100,
          ) / 100;
        const upperBorderData =
          Math.round(
            this.regressionData.upperConfidenceBorderData[index][1] * 100,
          ) / 100;
        return {
          x: data[0],
          y: data[1],
          "95% Confidence Interval": `[${lowerBorderData},${upperBorderData}]`,
        };
      })
      .sort((val1: any, val2: any) => val1.x - val2.x);

  prepareLineData = (dataPoints: any) =>
    dataPoints
      .map((data: any) => {
        return {
          x: data[0],
          y: data[1],
        };
      })
      .sort((val1: any, val2: any) => val1.x - val2.x);

  // ------------------------handeling----------------------------
  handleType = (tool: any, column: any) => {
    // @ts-expect-error TS(2339): Property 'tools' does not exist on type 'Readonly<... Remove this comment to see the full error message
    const colType = this.props.tools[tool].columns[column].type;
    if (colType === "text" || colType === "status") {
      return "ordinal";
    } else {
      // @ts-expect-error TS(2339): Property 'scaling' does not exist on type 'Readonl... Remove this comment to see the full error message
      return this.state.scaling === this.scalingOptions.logarithmic
        ? "log"
        : "linear";
    }
  };

  extractAxisInfoByName = (val: any, axis: any) => {
    let [toolIndex, colIdx] = val.split("-");
    return {
      [`data${axis}`]: val,
      [`tool${axis}`]: toolIndex,
      [`column${axis}`]: colIdx,
      [`name${axis}`]:
        // @ts-expect-error TS(2339): Property 'tools' does not exist on type 'Readonly<... Remove this comment to see the full error message
        this.props.tools[toolIndex].columns.find(
          (col: any) => col.colIdx === parseInt(colIdx),
        ).display_title +
        " (" +
        // @ts-expect-error TS(2339): Property 'tools' does not exist on type 'Readonly<... Remove this comment to see the full error message
        getRunSetName(this.props.tools[toolIndex]) +
        ")",
    };
  };

  setAxis = (ev: any, axis: any) => {
    this.array = [];
    let [tool, column] = ev.target.value.split("-");
    column = column.replace("___", "-");
    setURLParameter({ [`tool${axis}`]: tool, [`column${axis}`]: column });
  };

  swapAxes = () => {
    this.array = [];
    setURLParameter({
      // @ts-expect-error TS(2339): Property 'toolY' does not exist on type 'Readonly<... Remove this comment to see the full error message
      toolX: this.state.toolY,
      // @ts-expect-error TS(2339): Property 'toolX' does not exist on type 'Readonly<... Remove this comment to see the full error message
      toolY: this.state.toolX,
      // @ts-expect-error TS(2339): Property 'columnY' does not exist on type 'Readonl... Remove this comment to see the full error message
      columnX: this.state.columnY,
      // @ts-expect-error TS(2339): Property 'columnX' does not exist on type 'Readonl... Remove this comment to see the full error message
      columnY: this.state.columnX,
    });
  };

  render() {
    this.renderData();
    // @ts-expect-error TS(2339): Property 'scaling' does not exist on type 'Readonl... Remove this comment to see the full error message
    const isLinear = this.state.scaling === this.scalingOptions.linear;
    // @ts-expect-error TS(2339): Property 'isFlexible' does not exist on type 'Read... Remove this comment to see the full error message
    const Plot = this.props.isFlexible ? FlexibleXYPlot : XYPlot;
    // @ts-expect-error TS(2339): Property 'isFlexible' does not exist on type 'Read... Remove this comment to see the full error message
    const plotDimensions = this.props.isFlexible
      ? {
          height: window.innerHeight - 200,
        }
      : {
          height: 1000,
          width: 1500,
        };
    const highestAxisValue = this.maxX > this.maxY ? this.maxX : this.maxY;
    return (
      <div className="scatterPlot">
        // @ts-expect-error TS(2339): Property 'areAllColsHidden' does not exist on type... Remove this comment to see the full error message
        {!this.state.areAllColsHidden && this.renderAllSettings()}
        // @ts-expect-error TS(2769): No overload matches this call.
        <Plot
          className="scatterPlot__plot"
          margin={{ left: 90 }}
          // @ts-expect-error TS(2339): Property 'toolY' does not exist on type 'Readonly<... Remove this comment to see the full error message
          yType={this.handleType(this.state.toolY, this.state.columnY)}
          // @ts-expect-error TS(2339): Property 'toolX' does not exist on type 'Readonly<... Remove this comment to see the full error message
          xType={this.handleType(this.state.toolX, this.state.columnX)}
          xDomain={
            // @ts-expect-error TS(2339): Property 'toolX' does not exist on type 'Readonly<... Remove this comment to see the full error message
            this.handleType(this.state.toolX, this.state.columnX) !== "ordinal"
              ? [this.minX, this.maxX]
              : null
          }
          yDomain={
            // @ts-expect-error TS(2339): Property 'toolY' does not exist on type 'Readonly<... Remove this comment to see the full error message
            this.handleType(this.state.toolY, this.state.columnY) !== "ordinal"
              ? [this.minY, this.maxY]
              : null
          }
          {...plotDimensions}
        >
          <VerticalGridLines
            // @ts-expect-error TS(2322): Type '{ yType: string; xType: string; }' is not as... Remove this comment to see the full error message
            yType={this.handleType(this.state.toolY, this.state.columnY)}
            // @ts-expect-error TS(2339): Property 'toolX' does not exist on type 'Readonly<... Remove this comment to see the full error message
            xType={this.handleType(this.state.toolX, this.state.columnX)}
          />
          <HorizontalGridLines
            // @ts-expect-error TS(2322): Type '{ yType: string; xType: string; }' is not as... Remove this comment to see the full error message
            yType={this.handleType(this.state.toolY, this.state.columnY)}
            // @ts-expect-error TS(2339): Property 'toolX' does not exist on type 'Readonly<... Remove this comment to see the full error message
            xType={this.handleType(this.state.toolX, this.state.columnX)}
          />

          <DecorativeAxis
            className="middle-line"
            axisStart={{
              x: isLinear ? 0 : 1,
              y: isLinear ? 0 : 1,
            }}
            axisEnd={{
              x: highestAxisValue,
              y: highestAxisValue,
            }}
            axisDomain={[0, 10000000000]}
            style={{
              // @ts-expect-error TS(2769): No overload matches this call.
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
              // @ts-expect-error TS(2339): Property 'line' does not exist on type 'Readonly<{... Remove this comment to see the full error message
              x: isLinear ? 0 : this.state.line,
              y: isLinear ? 0 : 1,
            }}
            // @ts-expect-error TS(2339): Property 'line' does not exist on type 'Readonly<{... Remove this comment to see the full error message
            axisEnd={{ x: this.maxX, y: this.maxX / this.state.line }}
            axisDomain={[0, 10000000000]}
            style={{
              // @ts-expect-error TS(2769): No overload matches this call.
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
              // @ts-expect-error TS(2339): Property 'line' does not exist on type 'Readonly<{... Remove this comment to see the full error message
              y: isLinear ? 0 : this.state.line,
            }}
            // @ts-expect-error TS(2339): Property 'line' does not exist on type 'Readonly<{... Remove this comment to see the full error message
            axisEnd={{ x: this.maxX, y: this.maxX * this.state.line }}
            axisDomain={[0, 10000000000]}
            style={{
              // @ts-expect-error TS(2769): No overload matches this call.
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
            // @ts-expect-error TS(2339): Property 'nameX' does not exist on type 'Readonly<... Remove this comment to see the full error message
            title={this.state.nameX}
            tickFormat={(value) => value}
            // @ts-expect-error TS(2322): Type '{ title: any; tickFormat: (value: any) => an... Remove this comment to see the full error message
            yType={this.handleType(this.state.toolY, this.state.columnY)}
            // @ts-expect-error TS(2339): Property 'toolX' does not exist on type 'Readonly<... Remove this comment to see the full error message
            xType={this.handleType(this.state.toolX, this.state.columnX)}
          />
          <YAxis
            // @ts-expect-error TS(2339): Property 'nameY' does not exist on type 'Readonly<... Remove this comment to see the full error message
            title={this.state.nameY}
            tickFormat={(value) => value}
            // @ts-expect-error TS(2322): Type '{ title: any; tickFormat: (value: any) => an... Remove this comment to see the full error message
            yType={this.handleType(this.state.toolY, this.state.columnY)}
            // @ts-expect-error TS(2339): Property 'toolX' does not exist on type 'Readonly<... Remove this comment to see the full error message
            xType={this.handleType(this.state.toolX, this.state.columnX)}
          />
          <MarkSeries
            data={this.dataArray}
            // @ts-expect-error TS(6133): 'event' is declared but its value is never read.
            onValueMouseOver={(datapoint, event) =>
              this.setState({ value: datapoint })
            }
            // @ts-expect-error TS(6133): 'datapoint' is declared but its value is never rea... Remove this comment to see the full error message
            onValueMouseOut={(datapoint, event) =>
              this.setState({ value: null })
            }
          />
          // @ts-expect-error TS(2339): Property 'regression' does not exist on type 'Read... Remove this comment to see the full error message
          {this.state.regression !== this.regressionOptions.none &&
            this.checkForNumericalSelections() &&
            this.regressionData &&
            this.lineCount !== 0 &&
            this.renderRegressionAndConfidenceIntervals()}
          // @ts-expect-error TS(2339): Property 'value' does not exist on type 'Readonly<... Remove this comment to see the full error message
          {this.state.value ? <Hint value={this.state.value} /> : null}
        </Plot>
        // @ts-expect-error TS(2339): Property 'areAllColsHidden' does not exist on type... Remove this comment to see the full error message
        {this.state.areAllColsHidden ? (
          <div className="plot__noresults">No columns to show!</div>
        ) : (
          this.lineCount === 0 && (
            <div className="plot__noresults">
              No{" "}
              // @ts-expect-error TS(2339): Property 'results' does not exist on type 'Readonl... Remove this comment to see the full error message
              {this.state.results === this.resultsOptions.correct && "correct"}{" "}
              results
              // @ts-expect-error TS(2339): Property 'table' does not exist on type 'Readonly<... Remove this comment to see the full error message
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
