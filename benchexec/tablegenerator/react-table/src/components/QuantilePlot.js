// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import React from "react";
import "../../node_modules/react-vis/dist/style.css";
import {
  XYPlot,
  LineMarkSeries,
  VerticalGridLines,
  HorizontalGridLines,
  XAxis,
  YAxis,
  DiscreteColorLegend,
  Hint,
  makeWidthFlexible,
} from "react-vis";
import {
  getRunSetName,
  EXTENDED_DISCRETE_COLOR_RANGE,
  setParam,
  getHashSearch,
  getFirstVisibles,
} from "../utils/utils";

const plotOptions = {
  quantile: "Quantile",
  direct: "Direct",
};

const scalingOptions = {
  linear: "Linear",
  logarithmic: "Logarithmic",
};

const resultsOptions = {
  all: "All",
  correct: "Correct",
};

const defaultValues = {
  plot: plotOptions.quantile,
  scaling: scalingOptions.linear,
  results: resultsOptions.correct,
  UIDesign: 1,
  legendPosition: 1,
};

export default class QuantilePlot extends React.Component {
  constructor(props) {
    super(props);
    this.state = this.setup();
    this.possibleValues = [];
    this.lineCount = 1;
  }

  setup() {
    const queryProps = getHashSearch();

    let { selection, plot, scaling, results, UIDesign, legendPosition } = {
      ...defaultValues,
      ...queryProps,
    };

    const initialSelection = selection;
    const toolIdxes = this.props.tools.map((tool) => tool.toolIdx).join("");
    const runsetPattern = new RegExp("runset-[" + toolIdxes + "]");

    const isValue = selection === undefined || !runsetPattern.test(selection);

    if (isValue) {
      let selectedCol = selection
        ? this.props.tools
            .map((tool) => tool.columns)
            .flat()
            .find((col) => col.display_title === selection)
        : this.props.preSelection;

      /* If the defined col does not match any of the columns of the runsets or is not visible in any of the runsets,
         the first visible column that is not of the type status of the first visible runset will be shown instead. In case
         there is no such column, the first column of the type status will be selected. */
      if (!selectedCol || !this.isColVisibleInAnyTool(selectedCol)) {
        const [firstVisibleTool, firstVisibleColumn] = getFirstVisibles(
          this.props.tools,
          this.props.hiddenCols,
        );
        selectedCol =
          firstVisibleTool !== undefined
            ? this.props.tools
                .find((tool) => tool.toolIdx === firstVisibleTool)
                .columns.find((col) => col.colIdx === firstVisibleColumn)
            : undefined;
      }

      selection = selectedCol && selectedCol.display_title;
    } else {
      let toolIdx = parseInt(selection.split("-")[1]);
      const selectedTool = this.props.tools.find(
        (tool) => tool.toolIdx === toolIdx,
      );
      const hasToolAnyVisibleCols = selectedTool.columns.some(
        (col) => !this.props.hiddenCols[toolIdx].includes(col.colIdx),
      );

      /* If the selected runset has no visible cols, i.e. the runset itself is hidden, the first visible runset will be
         shown instead. */
      if (!hasToolAnyVisibleCols) {
        toolIdx = getFirstVisibles(this.props.tools, this.props.hiddenCols)[0];
      }
      selection = toolIdx !== undefined ? "runset-" + toolIdx : undefined;
    }

    /* If there was an initial selection (= URl parameter) and there is still a selection (= a visible column/runset) and
     they differ, then the initial selection was a hidden column/runset and therefore another column/runset was selected
     to be shown. In this case, update the URL parameter to correctly define the selection that is actually being shown now. */
    if (initialSelection && selection && initialSelection !== selection) {
      setParam({ selection });
    }

    return {
      selection,
      plot,
      scaling,
      results,
      isValue, //two versions of plot: one Value more RunSets => isValue:true; oneRunSet more Values => isValue:false
      UIDesign,
      legendPosition,
      isInvisible: [],
      areAllColsHidden: selection === undefined,
    };
  }

  isColRelevantForTool = (colIdx, toolIdx) =>
    !this.props.hiddenCols[toolIdx].includes(colIdx) &&
    colIdx.type !== "text" &&
    colIdx.type !== "status";

  isToolRelevantForCol = (tool, colName) => {
    const colInTool = tool.columns.find((col) => col.display_title === colName);
    return (
      tool.columns.length !== this.props.hiddenCols[tool.toolIdx].length &&
      colInTool &&
      !this.props.hiddenCols[tool.toolIdx].includes(colInTool.colIdx)
    );
  };

  // ----------------------resizer-------------------------------
  componentDidMount() {
    window.addEventListener("resize", this.updateDimensions);
    window.addEventListener("popstate", this.refreshUrlState);
  }

  componentWillUnmount() {
    window.removeEventListener("resize", this.updateDimensions);
    window.removeEventListener("popstate", this.refreshUrlState);
  }

  updateDimensions = () => {
    this.setState({
      width: window.innerWidth,
      height: window.innerHeight,
    });
  };

  refreshUrlState = () => {
    this.setState(this.setup());
  };

  isColVisibleInAnyTool(column) {
    return this.props.tools.some((tool) =>
      tool.columns.some(
        (col) =>
          col.colIdx === column.colIdx &&
          !this.props.hiddenCols[tool.toolIdx].includes(col.colIdx),
      ),
    );
  }

  // --------------------rendering-----------------------------
  renderLegend = () => {
    if (this.state.isValue) {
      return this.props.tools
        .filter((tool) => this.isToolRelevantForCol(tool, this.state.selection))
        .map(getRunSetName)
        .map((c) => {
          return {
            title: c,
            disabled: this.state.isInvisible.some((el) => el === c),
            strokeWidth: 4,
          };
        });
    } else {
      const tool = this.props.tools[this.state.selection.split("-")[1]];
      return !this.state.areAllColsHidden
        ? tool.columns
            .filter((col) =>
              this.isColRelevantForTool(col.colIdx, tool.toolIdx),
            )
            .map((c) => {
              return {
                title: c.display_title,
                disabled: this.state.isInvisible.some(
                  (el) => el === c.display_title,
                ),
                strokeWidth: 4,
              };
            })
        : [];
    }
  };

  renderAll = () => {
    const task = this.state.selection;

    if (this.state.isValue) {
      //var 1: compare different RunSets on one value
      this.props.tools.forEach((tool, i) => this.renderData(task, i, task + i));
    } else {
      //var 2: compare different values of one RunSet
      if (!this.state.areAllColsHidden) {
        const index = this.state.selection.split("-")[1];
        const tool = this.props.tools[index];
        tool.columns
          .filter(
            (col) =>
              this.isColRelevantForTool(col.colIdx, tool.toolIdx) &&
              !this.props.hiddenCols[index].includes(col.colIdx),
          )
          .forEach((column) =>
            this.renderData(column.display_title, index, column.display_title),
          );
      }
    }
  };

  renderData = (column, toolIdx, field) => {
    const isOrdinal = this.handleType() === "ordinal";
    let arrayY = [];
    const colIdx = this.props.tools[toolIdx].columns.findIndex(
      (value) => value.display_title === column,
    );

    if (
      !this.state.isValue ||
      (colIdx >= 0 && !this.props.hiddenCols[toolIdx].includes(colIdx))
    ) {
      arrayY = this.props.table.map((runSet) => {
        // Get y value if it should be shown and normalize it.
        // For correct x values, arrayY needs to have same length as table.
        const runResult = runSet.results[toolIdx];
        let value = null;
        if (
          this.state.results !== resultsOptions.correct ||
          runResult.category === "correct"
        ) {
          value = runResult.values[colIdx].raw;
          if (value === undefined) {
            value = null;
          }
          if (!isOrdinal && value !== null) {
            value = +value;
            if (!isFinite(value)) {
              value = null;
            }
          }
        }
        return [value, this.props.getRowName(runSet)];
      });

      if (this.state.plot === plotOptions.quantile) {
        arrayY = arrayY.filter((element) => element[0] !== null);
        arrayY = this.sortArray(arrayY, column);
      }
    }

    this.hasInvalidLog = false;
    const newArray = [];

    arrayY.forEach((el, i) => {
      const value = el[0];
      const isLogAndInvalid =
        this.state.scaling === scalingOptions.logarithmic && value <= 0;

      if (value !== null && !isLogAndInvalid) {
        newArray.push({
          x: i + 1,
          y: value,
          info: el[1],
        });
      }

      if (isLogAndInvalid) {
        this.hasInvalidLog = true;
      }
    });

    this[field] = newArray;
  };

  sortArray = (array, column) => {
    const currentValue = this.possibleValues.find(
      (value) => value.display_title === column,
    );

    return this.state.isValue && ["text", "status"].includes(currentValue.type)
      ? array.sort((a, b) => (a[0] > b[0] ? 1 : b[0] > a[0] ? -1 : 0))
      : array.sort((a, b) => +a[0] - +b[0]);
  };

  renderColumns = () => {
    this.props.tools.forEach((tool) => {
      tool.columns.forEach((column) => {
        if (
          !this.props.hiddenCols[tool.toolIdx].includes(column.colIdx) &&
          !this.possibleValues.some(
            (value) => value.display_title === column.display_title,
          )
        ) {
          this.possibleValues.push(column);
        }
      });
    });
    this.renderAll();
    return this.possibleValues.map((value) => {
      return (
        <option
          key={value.display_title}
          value={value.display_title}
          name={value.display_title}
        >
          {value.display_title}
        </option>
      );
    });
  };

  renderLines = () => {
    this.lineCount = 0;
    const color = () =>
      EXTENDED_DISCRETE_COLOR_RANGE[
        (this.lineCount - 1) % EXTENDED_DISCRETE_COLOR_RANGE.length
      ];

    if (this.state.isValue) {
      return this.props.tools
        .map((tool, i) => {
          // Cannot use filter() because we need original value of i
          if (!this.isToolRelevantForCol(tool, this.state.selection)) {
            return null;
          }
          const task = this.state.selection;
          const data = this[task + i];
          const id = getRunSetName(tool);
          this.lineCount++;

          return (
            <LineMarkSeries
              data={data}
              key={id}
              color={color()}
              opacity={this.handleLineState(id)}
              onValueMouseOver={(datapoint, event) =>
                this.setState({ value: datapoint })
              }
              onValueMouseOut={(datapoint, event) =>
                this.setState({ value: null })
              }
            />
          );
        })
        .filter((el) => !!el);
    } else {
      if (!this.state.areAllColsHidden) {
        const index = this.state.selection.split("-")[1];
        const tool = this.props.tools[index];
        return tool.columns
          .filter((col) => this.isColRelevantForTool(col.colIdx, tool.toolIdx))
          .map((column) => {
            const data = this[column.display_title];
            this.lineCount++;

            return (
              <LineMarkSeries
                data={data}
                key={column.display_title}
                color={color()}
                opacity={this.handleLineState(column.display_title)}
                onValueMouseOver={(datapoint, event) =>
                  this.setState({ value: datapoint })
                }
                onValueMouseOut={(datapoint, event) =>
                  this.setState({ value: null })
                }
              />
            );
          });
      }
    }
  };

  renderSettingOptions = (options, name) =>
    Object.values(options).map((option) => (
      <option value={option} key={option} name={option + " " + name}>
        {option + " " + name}
      </option>
    ));

  // ------------------------handeling----------------------------
  handleLineState = (line) => {
    return this.state.isInvisible.indexOf(line) < 0 ? 1 : 0;
  };

  setSelection = (ev) => {
    setParam({ selection: ev.target.value });
  };

  setPlot = (ev) => {
    setParam({ plot: ev.target.value });
  };

  setScaling = (ev) => {
    setParam({ scaling: ev.target.value });
  };

  setResults = (ev) => {
    setParam({ results: ev.target.value });
  };

  setUI = (ev) => {
    setParam({ UIDesign: ev.target.value });
  };

  setLegend = (ev) => {
    setParam({ legendPosition: ev.target.value });
  };

  toggleShow = ({ target }) => {
    this.setState({
      [target.name]: target.checked,
    });
  };

  handleType = () => {
    const { selection } = this.state;
    const index = this.possibleValues.findIndex(
      (value) => value.display_title === selection,
    );
    const type =
      this.state.isValue && index >= 0 ? this.possibleValues[index].type : null;
    return this.state.isValue && (type === "text" || type === "status")
      ? "ordinal"
      : this.state.scaling === scalingOptions.linear
      ? "linear"
      : "log";
  };

  renderPlot() {
    const FlexibleXYPlot = makeWidthFlexible(XYPlot);
    const areSelectionsOnTheRight =
      this.state.UIDesign > 3 && this.state.UIDesign < 6;
    if (!areSelectionsOnTheRight && this.state.legendPosition == 3) {
      return (
        <div className="plot-and-legend-container">
          <FlexibleXYPlot
            height={window.innerHeight - 200}
            margin={{ left: 90 }}
            yType={this.handleType()}
          >
            <VerticalGridLines />
            <HorizontalGridLines />
            <XAxis tickFormat={(value) => value} />
            <YAxis tickFormat={(value) => value} />
            {this.state.value ? <Hint value={this.state.value} /> : null}
            {this.renderLines()}
          </FlexibleXYPlot>
          <DiscreteColorLegend
            colors={EXTENDED_DISCRETE_COLOR_RANGE}
            items={this.renderLegend()}
            onItemClick={(Object, item) => {
              let line = "";
              line = Object.title.toString();
              if (this.state.isInvisible.indexOf(line) < 0) {
                this.setState({
                  isInvisible: this.state.isInvisible.concat([line]),
                });
              } else {
                return this.setState({
                  isInvisible: this.state.isInvisible.filter((l) => {
                    return l !== line;
                  }),
                });
              }
            }}
          />
        </div>
      );
    } else if (!areSelectionsOnTheRight && this.state.legendPosition == 4) {
      return (
        <FlexibleXYPlot
          height={window.innerHeight - 200}
          margin={{ left: 90 }}
          yType={this.handleType()}
        >
          <VerticalGridLines />
          <HorizontalGridLines />
          <XAxis tickFormat={(value) => value} />
          <YAxis tickFormat={(value) => value} />
          {this.state.value ? <Hint value={this.state.value} /> : null}
          {this.renderLines()}
          <DiscreteColorLegend
            className="legend-in-plot"
            colors={EXTENDED_DISCRETE_COLOR_RANGE}
            items={this.renderLegend()}
            onItemClick={(Object, item) => {
              let line = "";
              line = Object.title.toString();
              if (this.state.isInvisible.indexOf(line) < 0) {
                this.setState({
                  isInvisible: this.state.isInvisible.concat([line]),
                });
              } else {
                return this.setState({
                  isInvisible: this.state.isInvisible.filter((l) => {
                    return l !== line;
                  }),
                });
              }
            }}
          />
        </FlexibleXYPlot>
      );
    } else {
      return (
        <FlexibleXYPlot
          height={window.innerHeight - 200}
          margin={{ left: 90 }}
          yType={this.handleType()}
        >
          <VerticalGridLines />
          <HorizontalGridLines />
          <XAxis tickFormat={(value) => value} />
          <YAxis tickFormat={(value) => value} />
          {this.state.value ? <Hint value={this.state.value} /> : null}
          {this.renderLines()}
        </FlexibleXYPlot>
      );
    }
  }

  renderSettings() {
    const areSelectionsOnTheRight =
      this.state.UIDesign > 3 && this.state.UIDesign < 6;
    if (areSelectionsOnTheRight) {
      return (
        <div className="settings-container">
          <div className="setting">
            <span className="setting-label">Selection:</span>
            <select
              className="setting-select"
              name="Selection"
              value={this.state.selection}
              onChange={this.setSelection}
            >
              <optgroup label="Runsets">
                {this.props.tools.map((runset, i) => {
                  return runset.columns.length !==
                    this.props.hiddenCols[runset.toolIdx].length ? (
                    <option
                      key={"runset-" + i}
                      value={"runset-" + i}
                      name={"Runset " + i}
                    >
                      {getRunSetName(runset)}
                    </option>
                  ) : null;
                })}
              </optgroup>
              <optgroup label="Columns">{this.renderColumns()}</optgroup>
            </select>
          </div>
          <div className="setting">
            <span className="setting-label">Plot:</span>
            <select
              className="setting-select"
              name="Plot"
              value={this.state.plot}
              onChange={this.setPlot}
            >
              {this.renderSettingOptions(plotOptions, "Plot")}
            </select>
          </div>
          <div className="setting">
            <span className="setting-label">Scaling:</span>
            <select
              className="setting-select"
              name="Scaling"
              value={this.state.scaling}
              onChange={this.setScaling}
            >
              {this.renderSettingOptions(scalingOptions, "Scale")}
            </select>
          </div>
          <div className="setting">
            <span className="setting-label">Results:</span>
            <select
              className="setting-select"
              name="Results"
              value={this.state.results}
              onChange={this.setResults}
            >
              {this.renderSettingOptions(resultsOptions, "Results")}
            </select>
          </div>
          <div className="setting">
            {parseInt(this.state.UIDesign) === 5 && (
              <span className="setting-label">Legend:</span>
            )}
            <DiscreteColorLegend
              colors={EXTENDED_DISCRETE_COLOR_RANGE}
              items={this.renderLegend()}
              orientation="horizontal"
              onItemClick={(Object, item) => {
                let line = "";
                line = Object.title.toString();
                if (this.state.isInvisible.indexOf(line) < 0) {
                  this.setState({
                    isInvisible: this.state.isInvisible.concat([line]),
                  });
                } else {
                  return this.setState({
                    isInvisible: this.state.isInvisible.filter((l) => {
                      return l !== line;
                    }),
                  });
                }
              }}
            />
          </div>
        </div>
      );
    } else if (this.state.legendPosition == 2) {
      return (
        <div className="settings-container extracted-legend">
          <div className="extracted-settings">
            <div className="settings-subcontainer">
              <div className="setting">
                <span className="setting-label">Selection:</span>
                <select
                  className="setting-select"
                  name="Selection"
                  value={this.state.selection}
                  onChange={this.setSelection}
                >
                  <optgroup label="Runsets">
                    {this.props.tools.map((runset, i) => {
                      return runset.columns.length !==
                        this.props.hiddenCols[runset.toolIdx].length ? (
                        <option
                          key={"runset-" + i}
                          value={"runset-" + i}
                          name={"Runset " + i}
                        >
                          {getRunSetName(runset)}
                        </option>
                      ) : null;
                    })}
                  </optgroup>
                  <optgroup label="Columns">{this.renderColumns()}</optgroup>
                </select>
              </div>
              <div className="setting">
                <span className="setting-label">Plot:</span>
                <select
                  className="setting-select"
                  name="Plot"
                  value={this.state.plot}
                  onChange={this.setPlot}
                >
                  {this.renderSettingOptions(plotOptions, "Plot")}
                </select>
              </div>
            </div>
            <div className="settings-subcontainer">
              <div className="setting">
                <span className="setting-label">Scaling:</span>
                <select
                  className="setting-select"
                  name="Scaling"
                  value={this.state.scaling}
                  onChange={this.setScaling}
                >
                  {this.renderSettingOptions(scalingOptions, "Scale")}
                </select>
              </div>
              <div className="setting">
                <span className="setting-label">Results:</span>
                <select
                  className="setting-select"
                  name="Results"
                  value={this.state.results}
                  onChange={this.setResults}
                >
                  {this.renderSettingOptions(resultsOptions, "Results")}
                </select>
              </div>
            </div>
          </div>
          <div className="extracted-legend">
            <DiscreteColorLegend
              colors={EXTENDED_DISCRETE_COLOR_RANGE}
              items={this.renderLegend()}
              onItemClick={(Object, item) => {
                let line = "";
                line = Object.title.toString();
                if (this.state.isInvisible.indexOf(line) < 0) {
                  this.setState({
                    isInvisible: this.state.isInvisible.concat([line]),
                  });
                } else {
                  return this.setState({
                    isInvisible: this.state.isInvisible.filter((l) => {
                      return l !== line;
                    }),
                  });
                }
              }}
            />
          </div>
        </div>
      );
    } else if (
      this.state.legendPosition == 3 ||
      this.state.legendPosition == 4
    ) {
      return (
        <div className="settings-container">
          <div className="settings-subcontainer">
            <div className="setting">
              <span className="setting-label">Selection:</span>
              <select
                className="setting-select"
                name="Selection"
                value={this.state.selection}
                onChange={this.setSelection}
              >
                <optgroup label="Runsets">
                  {this.props.tools.map((runset, i) => {
                    return runset.columns.length !==
                      this.props.hiddenCols[runset.toolIdx].length ? (
                      <option
                        key={"runset-" + i}
                        value={"runset-" + i}
                        name={"Runset " + i}
                      >
                        {getRunSetName(runset)}
                      </option>
                    ) : null;
                  })}
                </optgroup>
                <optgroup label="Columns">{this.renderColumns()}</optgroup>
              </select>
            </div>
            <div className="setting">
              <span className="setting-label">Plot:</span>
              <select
                className="setting-select"
                name="Plot"
                value={this.state.plot}
                onChange={this.setPlot}
              >
                {this.renderSettingOptions(plotOptions, "Plot")}
              </select>
            </div>
          </div>
          <div className="settings-subcontainer">
            <div className="setting">
              <span className="setting-label">Scaling:</span>
              <select
                className="setting-select"
                name="Scaling"
                value={this.state.scaling}
                onChange={this.setScaling}
              >
                {this.renderSettingOptions(scalingOptions, "Scale")}
              </select>
            </div>
            <div className="setting">
              <span className="setting-label">Results:</span>
              <select
                className="setting-select"
                name="Results"
                value={this.state.results}
                onChange={this.setResults}
              >
                {this.renderSettingOptions(resultsOptions, "Results")}
              </select>
            </div>
          </div>
        </div>
      );
    } else {
      return (
        <div className="settings-container">
          <div className="settings-subcontainer">
            <div className="setting">
              <span className="setting-label">Selection:</span>
              <select
                className="setting-select"
                name="Selection"
                value={this.state.selection}
                onChange={this.setSelection}
              >
                <optgroup label="Runsets">
                  {this.props.tools.map((runset, i) => {
                    return runset.columns.length !==
                      this.props.hiddenCols[runset.toolIdx].length ? (
                      <option
                        key={"runset-" + i}
                        value={"runset-" + i}
                        name={"Runset " + i}
                      >
                        {getRunSetName(runset)}
                      </option>
                    ) : null;
                  })}
                </optgroup>
                <optgroup label="Columns">{this.renderColumns()}</optgroup>
              </select>
            </div>
            <div className="setting">
              <span className="setting-label">Plot:</span>
              <select
                className="setting-select"
                name="Plot"
                value={this.state.plot}
                onChange={this.setPlot}
              >
                {this.renderSettingOptions(plotOptions, "Plot")}
              </select>
            </div>
          </div>
          <div className="settings-subcontainer">
            <div className="setting">
              <span className="setting-label">Scaling:</span>
              <select
                className="setting-select"
                name="Scaling"
                value={this.state.scaling}
                onChange={this.setScaling}
              >
                {this.renderSettingOptions(scalingOptions, "Scale")}
              </select>
            </div>
            <div className="setting">
              <span className="setting-label">Results:</span>
              <select
                className="setting-select"
                name="Results"
                value={this.state.results}
                onChange={this.setResults}
              >
                {this.renderSettingOptions(resultsOptions, "Results")}
              </select>
            </div>
          </div>
          <div className="settings-subcontainer">
            <div className="setting">
              <DiscreteColorLegend
                colors={EXTENDED_DISCRETE_COLOR_RANGE}
                orientation="horizontal"
                items={this.renderLegend()}
                onItemClick={(Object, item) => {
                  let line = "";
                  line = Object.title.toString();
                  if (this.state.isInvisible.indexOf(line) < 0) {
                    this.setState({
                      isInvisible: this.state.isInvisible.concat([line]),
                    });
                  } else {
                    return this.setState({
                      isInvisible: this.state.isInvisible.filter((l) => {
                        return l !== line;
                      }),
                    });
                  }
                }}
              />
            </div>
          </div>
        </div>
      );
    }
  }

  render() {
    const areSelectionsOnTheRight =
      this.state.UIDesign > 3 && this.state.UIDesign < 6;
    return (
      <>
        <div className={"quantilePlot" + this.state.UIDesign}>
          {!this.state.areAllColsHidden && this.renderSettings()}
          {this.renderPlot()}
          {this.state.areAllColsHidden ? (
            <div className="plot__noresults">No columns to show!</div>
          ) : (
            this.lineCount === 0 && (
              <div className="plot__noresults">
                {this.hasInvalidLog
                  ? "All results have undefined values"
                  : "No correct results"}
              </div>
            )
          )}
        </div>
        <div
          style={{
            textAlign: "center",
            padding: ".5em",
            fontSize: "1.5em",
            backgroundColor: "#71bcff",
            width: "50%",
          }}
        >
          <span
            style={{
              paddingRight: "1em",
            }}
          >
            UI Design Selection:
          </span>
          <select
            style={{
              fontSize: "1em",
            }}
            name="UI"
            value={this.state.UIDesign}
            onChange={this.setUI}
          >
            <option value="1">1</option>
            <option value="2">2</option>
            <option value="3">3</option>
            <option value="4">4</option>
            <option value="5">5</option>
            <option value="6">6</option>
            <option value="7">7</option>
          </select>
          {!areSelectionsOnTheRight && (
            <span>
              <span
                style={{
                  padding: "0 1em",
                }}
              >
                Legend Position Selection:
              </span>
              <select
                style={{
                  fontSize: "1em",
                }}
                name="Legend"
                value={this.state.legendPosition}
                onChange={this.setLegend}
              >
                <option value="1">Inline with settings</option>
                <option value="2">Upper right corner</option>
                <option value="3">Next to plot</option>
                <option value="4">Lower right corner</option>
              </select>
            </span>
          )}
        </div>
      </>
    );
  }
}
