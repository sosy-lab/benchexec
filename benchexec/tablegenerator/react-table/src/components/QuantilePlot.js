// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import React from "react";
import "../../node_modules/react-vis/dist/style.css";
import {
  LineMarkSeries,
  VerticalGridLines,
  HorizontalGridLines,
  XAxis,
  YAxis,
  DiscreteColorLegend,
  Hint,
  XYPlot,
  FlexibleXYPlot,
} from "react-vis";
import {
  getRunSetName,
  EXTENDED_DISCRETE_COLOR_RANGE,
  setParam,
  getHashSearch,
  getFirstVisibles,
} from "../utils/utils";
import { renderSetting } from "../utils/plot";

export default class QuantilePlot extends React.Component {
  constructor(props) {
    super(props);

    this.plotOptions = {
      quantile: "Quantile Plot",
      direct: "Direct Plot",
    };

    this.scalingOptions = {
      linear: "Linear",
      logarithmic: "Logarithmic",
    };

    this.resultsOptions = {
      all: "All",
      correct: "Correct only",
    };

    this.defaultValues = {
      plot: this.plotOptions.quantile,
      scaling: this.scalingOptions.logarithmic,
      results: this.resultsOptions.correct,
    };

    this.checkForScoreBasedPlot();

    this.possibleValues = [];
    this.lineCount = 1;

    this.state = this.setPlotData();
  }

  setPlotData() {
    const queryProps = getHashSearch();

    let { selection, plot, scaling, results } = {
      ...this.defaultValues,
      ...queryProps,
    };

    const initialSelection = selection;
    const toolIdxes = this.props.tools.map((tool) => tool.toolIdx).join("");
    const runsetPattern = new RegExp("runset-[" + toolIdxes + "]");

    /* There are two versions of the plot:
       1. One columns of multiple runsets => isValue: true
       2. One Runset with all its columns => isValue: false */
    let isValue = selection === undefined || !runsetPattern.test(selection);
    selection = isValue
      ? this.getColumnSelection(selection)
      : this.getRunsetSelection(selection);

    /* If the plot is score-based and a runset is selected or the current selection doesn't support scores, select the first
       visible column that is not of the type status of the first visible runset that does support scores instead. If there is
       no such column, columns of the type status of such a runset will be taken into consideration too.
       In cases where the URL was manually changed and the component did not correctly update, it's possible there is no column
       that can be chosen. In this case the initial selection will be kept and an error message shown instead of the plot.
       This will be updated when selecting any new value. */
    if (
      plot === this.plotOptions.scoreBased &&
      ((isValue && !this.isInVisibleRunsetSupportingScore(selection)) ||
        !isValue)
    ) {
      this.setPossibleValues();
      let possibleCol = this.possibleValues.find(
        (col) =>
          col.type !== "status" &&
          this.isInVisibleRunsetSupportingScore(col.display_title),
      );
      if (!possibleCol) {
        possibleCol = this.possibleValues.find((col) =>
          this.isInVisibleRunsetSupportingScore(col.display_title),
        );
      }
      selection = possibleCol ? possibleCol.display_title : selection;
      isValue = true;
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
      isValue,
      isInvisible: [],
      areAllColsHidden: selection === undefined,
      isResultSelectionDisabled: plot === this.plotOptions.scoreBased,
    };
  }

  /** Returns the column that will be shown in the plot. If the selection defined in the URL is valid and is visible in
      any of the visible runsets, this selection will be returned. Otherwise the first visible column that is not of the
      type status of the first visible runset will be returned instead. In case there is no such column, the first column
      of the type status will be selected. */
  getColumnSelection(selection) {
    let selectedCol = selection
      ? this.props.tools
          .map((tool) => tool.columns)
          .flat()
          .find((col) => col.display_title === selection)
      : this.props.preSelection;
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

    return selectedCol && selectedCol.display_title;
  }

  /** Returns the runset that will be shown in the plot. If the selected runset has no visible columns, i.e. the runset
      itself is hidden, the first visible runset will be returned instead. */
  getRunsetSelection(selection) {
    let toolIdx = parseInt(selection.split("-")[1]);
    const selectedTool = this.props.tools.find(
      (tool) => tool.toolIdx === toolIdx,
    );
    const hasToolAnyVisibleCols = selectedTool.columns.some((col) =>
      this.isColVisible(toolIdx, col.colIdx),
    );

    if (!hasToolAnyVisibleCols) {
      toolIdx = getFirstVisibles(this.props.tools, this.props.hiddenCols)[0];
    }
    return toolIdx !== undefined ? "runset-" + toolIdx : undefined;
  }

  /* Checks whether any of the visible runsets supports a score based plot and adds the score-based option to the
    dropdown if applicable. In case all visible runsets support a score based plot, the score-based quantile plot
    will be set as default. */
  checkForScoreBasedPlot() {
    if (
      this.props.tools.some(
        (tool) => tool.scoreBased && this.isToolVisible(tool),
      )
    ) {
      this.plotOptions = {
        scoreBased: "Score-based Quantile Plot",
        ...this.plotOptions,
      };
      if (
        this.props.tools.every(
          (tool) => tool.scoreBased && this.isToolVisible(tool),
        )
      ) {
        this.defaultValues.plot = this.plotOptions.scoreBased;
      }
    }
  }

  isColRelevantForTool = (colIdx, toolIdx) =>
    this.isColVisible(toolIdx, colIdx) &&
    colIdx.type !== "text" &&
    colIdx.type !== "status";

  isToolRelevantForCol = (tool, colName) => {
    const colInTool = tool.columns.find((col) => col.display_title === colName);
    return (
      this.isToolVisible(tool) &&
      colInTool &&
      this.isColVisible(tool.toolIdx, colInTool.colIdx)
    );
  };

  isColVisibleInAnyTool = (column) =>
    this.props.tools.some((tool) =>
      tool.columns.some(
        (col) =>
          col.colIdx === column.colIdx &&
          this.isColVisible(tool.toolIdx, col.colIdx),
      ),
    );

  // Checks whether the given column (defined by its display title) is part of any visible runset that supports a scoring scheme.
  isInVisibleRunsetSupportingScore = (colTitle) =>
    this.props.tools
      .filter((tool) => this.isToolVisible(tool))
      .some(
        (tool) =>
          tool.scoreBased &&
          tool.columns.some((col) => col.display_title === colTitle),
      );

  isToolVisible = (tool) =>
    tool.columns.length !== this.props.hiddenCols[tool.toolIdx].length;

  isColVisible = (toolIdx, colIdx) =>
    !this.props.hiddenCols[toolIdx].includes(colIdx);

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
      height: window.innerHeight,
    });
  };

  refreshUrlState = () => {
    this.setState(this.setPlotData());
  };

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
      /* Option 1: Compare different runsets on one value.
         If the score-based plot is selected, only runsets that support scoring schemes are shown. */
      const tools =
        this.state.plot === this.plotOptions.scoreBased
          ? this.props.tools.filter((tool) => tool.scoreBased)
          : this.props.tools;
      tools.forEach((tool) =>
        this.renderData(task, tool.toolIdx, task + tool.toolIdx),
      );
    } else {
      /* Option 2: Compare different values on one runset. */
      if (!this.state.areAllColsHidden) {
        const index = this.state.selection.split("-")[1];
        const tool = this.props.tools[index];
        tool.columns
          .filter(
            (col) =>
              this.isColRelevantForTool(col.colIdx, tool.toolIdx) &&
              this.isColVisible(tool.toolIdx, col.colIdx),
          )
          .forEach((column) =>
            this.renderData(column.display_title, index, column.display_title),
          );
      }
    }
  };

  renderData = (colTitle, toolIdx, field) => {
    const isPlotScoreBased = this.state.plot === this.plotOptions.scoreBased;
    const isOrdinal = this.handleType() === "ordinal";
    const colIdx = this.props.tools[toolIdx].columns.findIndex(
      (value) => value.display_title === colTitle,
    );
    let arrayY = [];
    let scoreOfIncorrectResults = 0;

    if (
      !this.state.isValue ||
      (colIdx >= 0 && this.isColVisible(toolIdx, colIdx))
    ) {
      arrayY = this.props.table.map((runSet) => {
        // Get y value if it should be shown and normalize it.
        // For correct x values, arrayY needs to have same length as table.
        const runResult = runSet.results[toolIdx];
        let value = null;
        if (
          runResult.category === "correct" ||
          (!this.state.isResultSelectionDisabled &&
            this.state.results !== this.resultsOptions.correct)
        ) {
          value = runResult.values[colIdx].raw || null;
          if (!isOrdinal && value !== null) {
            value = isFinite(+value) ? +value : null;
          }
        } else if (
          isPlotScoreBased &&
          runResult.score &&
          runResult.category !== "correct"
        ) {
          scoreOfIncorrectResults += runResult.score;
        }
        return {
          value,
          rowName: this.props.getRowName(runSet),
          score: runResult.score,
        };
      });

      if (this.state.plot !== this.plotOptions.direct) {
        arrayY = arrayY.filter((dataObj) => dataObj.value !== null);
        arrayY = this.sortArray(arrayY, colTitle);
      }
    }

    this.hasInvalidLog = false;
    const newArray = [];
    let xPosition = isPlotScoreBased ? scoreOfIncorrectResults : 0;
    arrayY.forEach(({ value, rowName, score }) => {
      const isLogAndInvalid =
        this.state.scaling === this.scalingOptions.logarithmic && value <= 0;
      xPosition = xPosition + (isPlotScoreBased ? score : 1);

      if (value !== null && !isLogAndInvalid) {
        newArray.push({
          x: xPosition,
          y: value,
          info: rowName,
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
      ? array.sort((a, b) =>
          a.value > b.value ? 1 : b.value > a.value ? -1 : 0,
        )
      : array.sort((a, b) => +a.value - +b.value);
  };

  setPossibleValues() {
    this.props.tools.forEach((tool) => {
      tool.columns.forEach((col) => {
        if (
          this.isColVisible(tool.toolIdx, col.colIdx) &&
          !this.possibleValues.some(
            (value) => value.display_title === col.display_title,
          )
        ) {
          this.possibleValues.push(col);
        }
      });
    });
  }

  renderColumns = () => {
    return this.possibleValues.map((value) => {
      const isDisabled =
        this.state.plot === this.plotOptions.scoreBased &&
        !this.isInVisibleRunsetSupportingScore(value.display_title);
      return (
        <option
          key={value.display_title}
          value={value.display_title}
          name={value.display_title}
          disabled={isDisabled}
          className={isDisabled ? "disabled" : ""}
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
      return (
        this.props.tools
          // Cannot use filter() because we need original value of i
          .map((tool, i) => {
            if (
              !this.isToolRelevantForCol(tool, this.state.selection) ||
              (this.state.plot === this.plotOptions.scoreBased &&
                !tool.scoreBased)
            ) {
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
          .filter((el) => !!el)
      );
    } else if (!this.state.areAllColsHidden) {
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
  };

  renderAllSettings() {
    const resultsTooltip =
      this.state.plot === this.plotOptions.scoreBased
        ? "Score-based Quantile Plots always show correct results offset by the score of wrong results. Any defined filters will still be applied."
        : "In addition to which results are selected here, any defined filters will still be applied.";
    return (
      <div className="settings-legend-container">
        <div className="settings-container">
          <div className="settings-border-container">
            <div className="settings-subcontainer flexible-width">
              <div className="setting flexible-width">
                <span className="setting-label">Selection:</span>
                <select
                  className="setting-select"
                  name="setting-Selection"
                  value={this.state.selection}
                  onChange={(ev) => setParam({ selection: ev.target.value })}
                >
                  <optgroup label="Runsets">
                    {this.props.tools.map((tool, i) => {
                      const isDisabled =
                        this.state.plot === this.plotOptions.scoreBased;
                      return this.isToolVisible(tool) ? (
                        <option
                          key={"runset-" + i}
                          value={"runset-" + i}
                          name={"Runset " + i}
                          disabled={isDisabled}
                          className={isDisabled ? "disabled" : ""}
                        >
                          {getRunSetName(tool)}
                        </option>
                      ) : null;
                    })}
                  </optgroup>
                  <optgroup label="Columns">{this.renderColumns()}</optgroup>
                </select>
              </div>
              {renderSetting(
                "Plot",
                this.state.plot,
                (ev) => setParam({ plot: ev.target.value }),
                this.plotOptions,
              )}
            </div>
            <div className="settings-subcontainer">
              {renderSetting(
                "Scaling",
                this.state.scaling,
                (ev) => setParam({ scaling: ev.target.value }),
                this.scalingOptions,
              )}
              {renderSetting(
                "Results",
                this.state.results,
                (ev) => setParam({ results: ev.target.value }),
                this.resultsOptions,
                resultsTooltip,
                this.state.isResultSelectionDisabled,
              )}
            </div>
          </div>
        </div>
        <div>
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
  }

  // ------------------------handeling----------------------------
  handleLineState = (line) => {
    return this.state.isInvisible.indexOf(line) < 0 ? 1 : 0;
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
      : this.state.scaling === this.scalingOptions.linear
      ? "linear"
      : "log";
  };

  render() {
    this.setPossibleValues();
    this.renderAll();
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
      <div className="quantilePlot">
        {!this.state.areAllColsHidden && this.renderAllSettings()}
        <Plot
          margin={{ left: 90 }}
          yType={this.handleType()}
          {...plotDimensions}
        >
          <VerticalGridLines />
          <HorizontalGridLines />
          <XAxis tickFormat={(value) => value} />
          <YAxis tickFormat={(value) => value} />
          {this.state.value ? <Hint value={this.state.value} /> : null}
          {this.renderLines()}
        </Plot>
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
    );
  }
}
