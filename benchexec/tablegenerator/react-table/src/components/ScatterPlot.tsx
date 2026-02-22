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
import calcRegression from "regression";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faExchangeAlt } from "@fortawesome/free-solid-svg-icons";

import type { RowLike, ToolLike } from "../types/reactTable";

/* ============================================================================
 * Types: helpers and component props/state
 * ============================================================================
 */

type AxisId = "X" | "Y";

type ScalingType = "ordinal" | "log" | "linear";

type ScatterPlotProps = {
  tools: ToolLike[];
  columns: Array<[unknown, string]>;
  hiddenCols: Record<number, number[]>;
  table: RowLike[];
  getRowName: (row: RowLike) => string;
  isFlexible?: boolean;
}

type ScatterPlotState = {
  dataX?: string;
  dataY?: string;
  results: string;
  scaling: string;
  regression: string;
  toolX: number;
  toolY: number;
  line: number;
  columnX: number;
  columnY: number;
  nameX: string;
  nameY: string;
  value: ScatterPlotPoint | null | false;
  areAllColsHidden: boolean;
}

/** A single scatter-plot point. */
type ScatterPlotPoint = {
  x: number;
  y: number;
  info: string;
}

type SettingOptions = Record<string, string>;

type OptgroupOption = {
  name: string;
  value: string;
}

type OptgroupOptions = Record<string, OptgroupOption[]>;

/**
 * Minimal subset of the regression result shape that we use.
 * (The regression library types are not necessarily available in this project.)
 */
interface RegressionResultLike {
  points: Array<[number, number]>;
  equation: [number, number];
  string: string;
  r2: number;
  predict: (x: number) => [number, number];
}

interface RegressionData {
  regression: RegressionResultLike;
  text: string;
  upperConfidenceBorderData: Array<[number, number]>;
  lowerConfidenceBorderData: Array<[number, number]>;
}

/** URL parameters that ScatterPlot may read/write. */
interface ScatterPlotUrlParams {
  results?: string | null;
  scaling?: string | null;
  toolX?: string | null;
  toolY?: string | null;
  columnX?: string | null;
  columnY?: string | null;
  line?: string | null;
  regression?: string | null;
}

export default class ScatterPlot extends React.Component<
  ScatterPlotProps,
  ScatterPlotState
> {
  scalingOptions: SettingOptions;

  resultsOptions: SettingOptions;

  regressionOptions: SettingOptions;

  lineOptgroupOptions: Record<string, Array<{ name: string; value: number }>>;

  defaultValues: {
    scaling: string;
    results: string;
    regression: string;
    line: number;
  };

  maxX: number;

  minX: number;

  maxY: number;

  minY: number;

  lineCount: number;

  hasInvalidLog: boolean;

  dataArray: ScatterPlotPoint[];

  regressionData?: RegressionData;

  // NOTE (JS->TS): This field existed implicitly in JS; keep it as an empty list to preserve structure.
  array: unknown[];

  constructor(props: ScatterPlotProps) {
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
      line: Object.values(this.lineOptgroupOptions)[0][11].value,
    };

    this.state = this.setup();
    this.maxX = 0;
    this.minX = 0;
    this.maxY = 0;
    this.minY = 0;
    this.lineCount = 1;
    this.hasInvalidLog = false;
    this.dataArray = [];
    this.array = [];
  }

  setup(): ScatterPlotState {
    const defaultName =
      getRunSetName(this.props.tools[0]) + " " + this.props.columns[0][1];

    const urlParams = getURLParameters() as Partial<ScatterPlotUrlParams>;

    const {
      results,
      scaling,
      toolX,
      toolY,
      columnX,
      columnY,
      line,
      regression,
    } = {
      ...this.defaultValues,
      ...urlParams,
    } as {
      results: string;
      scaling: string;
      regression: string;
      line: number | string;
      toolX?: string | null;
      toolY?: string | null;
      columnX?: string | null;
      columnY?: string | null;
    };

    let dataX: string | undefined;
    let dataY: string | undefined;
    let areAllColsHidden: boolean;

    const parsedLine =
      typeof line === "string" ? Number.parseFloat(line) : line;

    let toolXNum: number | undefined;
    let toolYNum: number | undefined;
    let columnXNum: number | undefined;
    let columnYNum: number | undefined;

    if (!isNil(toolX) && !isNil(columnX)) {
      toolXNum = Number.parseInt(toolX, 10);
      columnXNum = Number.parseInt(columnX, 10);
    }
    if (!isNil(toolY) && !isNil(columnY)) {
      toolYNum = Number.parseInt(toolY, 10);
      columnYNum = Number.parseInt(columnY, 10);
    }

    if (isNil(toolXNum) || isNil(columnXNum)) {
      const [firstVisibleTool, firstVisibleColumn] = getFirstVisibles(
        this.props.tools,
        this.props.hiddenCols,
      ) as [number | undefined, number | undefined];
      areAllColsHidden = firstVisibleTool === undefined;
      toolXNum = firstVisibleTool ?? 0;
      columnXNum = firstVisibleColumn ?? 0;
      dataX =
        firstVisibleTool !== undefined && firstVisibleColumn !== undefined
          ? `${firstVisibleTool}-${firstVisibleColumn}`
          : undefined;
    } else {
      areAllColsHidden = false;
      dataX = `${toolXNum}-${columnXNum}`;
    }

    if (isNil(toolYNum) || isNil(columnYNum)) {
      const [firstVisibleTool, firstVisibleColumn] = getFirstVisibles(
        this.props.tools,
        this.props.hiddenCols,
      ) as [number | undefined, number | undefined];
      areAllColsHidden = firstVisibleTool === undefined;
      toolYNum = firstVisibleTool ?? 0;
      columnYNum = firstVisibleColumn ?? 0;
      dataY =
        firstVisibleTool !== undefined && firstVisibleColumn !== undefined
          ? `${firstVisibleTool}-${firstVisibleColumn}`
          : undefined;
    } else {
      areAllColsHidden = false;
      dataY = `${toolYNum}-${columnYNum}`;
    }

    let out: ScatterPlotState = {
      dataX,
      dataY,
      results,
      scaling,
      regression,
      toolX: 0,
      toolY: 0,
      line: Number.isFinite(parsedLine) ? parsedLine : this.defaultValues.line,
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

  refreshUrlState = (): void => {
    this.setState(this.setup());
  };

  checkForNumericalSelections = (): boolean =>
    this.handleType(this.state.toolY, this.state.columnY) !== "ordinal" &&
    this.handleType(this.state.toolX, this.state.columnX) !== "ordinal";

  // --------------------rendering-----------------------------
  renderData = (): void => {
    const array: ScatterPlotPoint[] = [];
    this.hasInvalidLog = false;

    if (!this.state.areAllColsHidden) {
      this.props.table.forEach((row) => {
        const resX = row.results[this.state.toolX];
        const resY = row.results[this.state.toolY];
        const x = resX.values[this.state.columnX].raw as number | null;
        const y = resY.values[this.state.columnY].raw as number | null;
        const hasValues =
          x !== undefined && x !== null && y !== undefined && y !== null;
        const areOnlyCorrectResults =
          this.state.results === this.resultsOptions.correct;

        if (
          hasValues &&
          (!areOnlyCorrectResults ||
            (areOnlyCorrectResults &&
              resX.category === "correct" &&
              resY.category === "correct"))
        ) {
          const isLogAndInvalid =
            this.state.scaling === this.scalingOptions.logarithmic &&
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

    const isRegressionEnabled =
      this.state.regression !== this.regressionOptions.none;
    const areSelectionsNumerical = this.checkForNumericalSelections();
    if (isRegressionEnabled) {
      if (this.lineCount === 0 || !areSelectionsNumerical) {
        setURLParameter({ regression: this.regressionOptions.none });
      } else {
        const regressionDataArray: Array<[number, number]> = array.map(
          (data) => [parseFloat(`${data.x}`), parseFloat(`${data.y}`)],
        );
        const regression = calcRegression.linear(
          regressionDataArray,
        ) as unknown as RegressionResultLike;

        const confidenceIntervalBorders = getConfidenceIntervalBorders(
          regressionDataArray,
          regression.points,
          regression.predict,
          this.minX,
          this.maxX,
        ) as {
          upperBorderData: Array<[number, number]>;
          lowerBorderData: Array<[number, number]>;
        };

        /* Due to points with same x but different y value, there may be many duplicates in the regression data. Those can be used for
           easier calculation for the 95% Confidence Intervals, but aren't necessary afterwards since they'll only be used to draw the line.
           To have a line from the start to the end of the coordinate system, the points at the borders are added here too. */
        const endPoints: Array<[number, number]> = [
          [this.minX, regression.predict(this.minX)[1]],
          [this.maxX, regression.predict(this.maxX)[1]],
        ];
        regression.points = Array.from(
          new Set(regression.points.map(JSON.stringify)),
          JSON.parse,
        ).concat(endPoints) as Array<[number, number]>;

        const unitX =
          this.props.tools[this.state.toolX].columns[this.state.columnX].unit;
        const unitY =
          this.props.tools[this.state.toolY].columns[this.state.columnY].unit;
        const helpText = `Estimation technique: ordinary least squares (OLS)
                          Predictor variable (X-Axis) in ${unitX}: ${this.state.nameX}
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

  setMinMaxValues = (array: ScatterPlotPoint[]): void => {
    const xValues = array.map((el) => el.x);
    const yValues = array.map((el) => el.y);

    this.maxX = this.findMaxValue(xValues);
    this.maxY = this.findMaxValue(yValues);
    this.minX = this.findMinValue(xValues);
    this.minY = this.findMinValue(yValues);
  };

  findMaxValue = (values: number[]): number => {
    const max = Math.max(...values);
    return max < 3 ? 3 : max;
  };

  findMinValue = (values: number[]): number => {
    const min = Math.min(...values);
    return min > 2 ? 1 : min;
  };

  renderAllSettings(): JSX.Element {
    const axisOptions = this.props.tools.reduce<OptgroupOptions>(
      (acc, runset, runsetIdx) =>
        Object.assign(acc, {
          [getRunSetName(runset)]: runset.columns
            .filter(
              (col) => !this.props.hiddenCols[runsetIdx].includes(col.colIdx),
            )
            .map((col) => ({
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
              (ev: React.ChangeEvent<HTMLSelectElement>) =>
                this.setAxis(ev, "X"),
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
              (ev: React.ChangeEvent<HTMLSelectElement>) =>
                this.setAxis(ev, "Y"),
              axisOptions,
            )}
          </div>
          <div className="settings-subcontainer">
            {renderSetting(
              "Scaling",
              this.state.scaling,
              (ev: React.ChangeEvent<HTMLSelectElement>) =>
                setURLParameter({ scaling: ev.target.value }),
              this.scalingOptions,
            )}
            {renderSetting(
              "Results",
              this.state.results,
              (ev: React.ChangeEvent<HTMLSelectElement>) =>
                setURLParameter({ results: ev.target.value }),
              this.resultsOptions,
              "In addition to which results are selected here, any filters will still be applied.",
            )}
            <div className="settings-subcontainer">
              {renderOptgroupsSetting(
                "Aux. Lines",
                `${this.state.line}`,
                (ev: React.ChangeEvent<HTMLSelectElement>) =>
                  setURLParameter({ line: ev.target.value }),
                this.lineOptgroupOptions as unknown as OptgroupOptions,
                "Adds the two auxiliary lines f(x) = cx and f(x) = x/c to the plot, with c being the chosen factor in the dropdown.",
              )}
            </div>
          </div>
          <div className="settings-subcontainer">
            {renderSetting(
              "Regression",
              this.state.regression,
              (ev: React.ChangeEvent<HTMLSelectElement>) => {
                if (this.checkForNumericalSelections()) {
                  setURLParameter({ regression: ev.target.value });
                } else {
                  alert(
                    "Regressions are only available for numerical selections.",
                  );
                }
              },
              this.regressionOptions,
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

  renderRegressionAndConfidenceIntervals(): React.ReactNode[] {
    const minX = Math.floor(this.minX);
    const maxX = Math.ceil(this.maxX);
    const dataPointsOfRegression = getDataPointsOfRegression(
      minX,
      maxX,
      this.regressionData?.regression.predict,
    ) as Array<[number, number]>;
    return [
      this.renderConfidenceIntervalLine(
        this.regressionData?.upperConfidenceBorderData ?? [],
        "upper",
      ),
      this.renderConfidenceIntervalLine(
        this.regressionData?.lowerConfidenceBorderData ?? [],
        "lower",
      ),
      this.renderRegressionLine(dataPointsOfRegression),
    ];
  }

  renderRegressionLine = (dataPoints: Array<[number, number]>): JSX.Element => {
    const lineData = this.prepareRegressionLineData(dataPoints);
    return (
      <LineMarkSeries
        className="regression-line"
        data={lineData as unknown as Array<Record<string, unknown>>}
        style={{
          stroke: "green",
        }}
        key={"reg-line-" + dataPoints}
        onValueMouseOver={(datapoint: unknown) =>
          this.setState({ value: datapoint as ScatterPlotPoint })
        }
        onValueMouseOut={() => this.setState({ value: null })}
        opacity="0"
      />
    );
  };

  renderConfidenceIntervalLine = (
    dataPoints: Array<[number, number]>,
    identifier: string,
  ): JSX.Element => {
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

  prepareRegressionLineData = (
    dataPoints: Array<[number, number]>,
  ): Array<{ x: number; y: number; "95% Confidence Interval": string }> =>
    dataPoints
      .sort((val1, val2) => val1[0] - val2[0])
      .map((data, index) => {
        const lowerBorderData =
          Math.round(
            (this.regressionData?.lowerConfidenceBorderData[index]?.[1] ?? 0) *
              100,
          ) / 100;
        const upperBorderData =
          Math.round(
            (this.regressionData?.upperConfidenceBorderData[index]?.[1] ?? 0) *
              100,
          ) / 100;
        return {
          x: data[0],
          y: data[1],
          "95% Confidence Interval": `[${lowerBorderData},${upperBorderData}]`,
        };
      })
      .sort((val1, val2) => val1.x - val2.x);

  prepareLineData = (
    dataPoints: Array<[number, number]>,
  ): Array<{ x: number; y: number }> =>
    dataPoints
      .map((data) => {
        return {
          x: data[0],
          y: data[1],
        };
      })
      .sort((val1, val2) => val1.x - val2.x);

  // ------------------------handeling----------------------------
  handleType = (tool: number, column: number): ScalingType => {
    const colType = this.props.tools[tool].columns[column].type;
    if (colType === "text" || colType === "status") {
      return "ordinal";
    } else {
      return this.state.scaling === this.scalingOptions.logarithmic
        ? "log"
        : "linear";
    }
  };

  extractAxisInfoByName = (
    val: string,
    axis: AxisId,
  ): Partial<ScatterPlotState> => {
    const [toolIndexRaw, colIdxRaw] = val.split("-");
    const toolIndex = Number.parseInt(toolIndexRaw, 10);
    const colIdx = Number.parseInt(colIdxRaw, 10);

    return {
      [`data${axis}`]: val,
      [`tool${axis}`]: toolIndex,
      [`column${axis}`]: colIdx,
      [`name${axis}`]:
        this.props.tools[toolIndex].columns.find((col) => col.colIdx === colIdx)
          ?.display_title +
        " (" +
        getRunSetName(this.props.tools[toolIndex]) +
        ")",
    } as Partial<ScatterPlotState>;
  };

  setAxis = (ev: React.ChangeEvent<HTMLSelectElement>, axis: AxisId): void => {
    this.array = [];
    let [tool, column] = ev.target.value.split("-");
    column = column.replace("___", "-");
    setURLParameter({ [`tool${axis}`]: tool, [`column${axis}`]: column });
  };

  swapAxes = (): void => {
    this.array = [];
    setURLParameter({
      toolX: this.state.toolY,
      toolY: this.state.toolX,
      columnX: this.state.columnY,
      columnY: this.state.columnX,
    });
  };

  render(): JSX.Element {
    this.renderData();
    const isLinear = this.state.scaling === this.scalingOptions.linear;
    const Plot = this.props.isFlexible ? FlexibleXYPlot : XYPlot;
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
              x: highestAxisValue,
              y: highestAxisValue,
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
            data={this.dataArray as unknown as Array<Record<string, unknown>>}
            onValueMouseOver={(datapoint: unknown) =>
              this.setState({ value: datapoint as ScatterPlotPoint })
            }
            onValueMouseOut={() => this.setState({ value: null })}
          />
          {this.state.regression !== this.regressionOptions.none &&
            this.checkForNumericalSelections() &&
            this.regressionData &&
            this.lineCount !== 0 &&
            this.renderRegressionAndConfidenceIntervals()}
          {this.state.value ? (
            <Hint
              value={this.state.value as unknown as Record<string, unknown>}
            />
          ) : null}
        </Plot>
        {this.state.areAllColsHidden ? (
          <div className="plot__noresults">No columns to show!</div>
        ) : (
          this.lineCount === 0 && (
            <div className="plot__noresults">
              No{" "}
              {this.state.results === this.resultsOptions.correct && "correct"}{" "}
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
