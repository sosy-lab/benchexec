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
  setURLParameter,
  getURLParameters,
  getFirstVisibles,
} from "../utils/utils";
import { renderResetButton, renderSetting } from "../utils/plot";

export default class QuantilePlot extends React.Component {
  defaultValues: any;
  hasInvalidLog: any;
  lineCount: any;
  plotOptions: any;
  possibleValues: any;
  resultsOptions: any;
  scalingOptions: any;
  constructor(props: any) {
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
    // @ts-expect-error TS(2554): Expected 1 arguments, but got 0.
    const queryProps = getURLParameters();

    let { selection, plot, scaling, results }: any = {
      ...this.defaultValues,
      ...queryProps,
    };

    const initialSelection = selection;
    // @ts-expect-error TS(2339): Property 'tools' does not exist on type 'Readonly<... Remove this comment to see the full error message
    const toolIdxes = this.props.tools
      .map((tool: any) => tool.toolIdx)
      .join("");
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
        (col: any) =>
          col.type !== "status" &&
          this.isInVisibleRunsetSupportingScore(col.display_title),
      );
      if (!possibleCol) {
        possibleCol = this.possibleValues.find((col: any) =>
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
      setURLParameter({ selection });
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
  getColumnSelection(selection: any) {
    let selectedCol = selection
      // @ts-expect-error TS(2339): Property 'tools' does not exist on type 'Readonly<... Remove this comment to see the full error message
      ? this.props.tools
          .map((tool: any) => tool.columns)
          .flat()
          .find((col: any) => col.display_title === selection)
      // @ts-expect-error TS(2339): Property 'preSelection' does not exist on type 'Re... Remove this comment to see the full error message
      : this.props.preSelection;
    if (!selectedCol || !this.isColVisibleInAnyTool(selectedCol)) {
      const [firstVisibleTool, firstVisibleColumn] = getFirstVisibles(
        // @ts-expect-error TS(2339): Property 'tools' does not exist on type 'Readonly<... Remove this comment to see the full error message
        this.props.tools,
        // @ts-expect-error TS(2339): Property 'hiddenCols' does not exist on type 'Read... Remove this comment to see the full error message
        this.props.hiddenCols,
      );
      selectedCol =
        firstVisibleTool !== undefined
          // @ts-expect-error TS(2339): Property 'tools' does not exist on type 'Readonly<... Remove this comment to see the full error message
          ? this.props.tools
              .find((tool: any) => tool.toolIdx === firstVisibleTool)
              .columns.find((col: any) => col.colIdx === firstVisibleColumn)
          : undefined;
    }

    return selectedCol && selectedCol.display_title;
  }

  /** Returns the runset that will be shown in the plot. If the selected runset has no visible columns, i.e. the runset
      itself is hidden, the first visible runset will be returned instead. */
  getRunsetSelection(selection: any) {
    let toolIdx = parseInt(selection.split("-")[1]);
    // @ts-expect-error TS(2339): Property 'tools' does not exist on type 'Readonly<... Remove this comment to see the full error message
    const selectedTool = this.props.tools.find(
      (tool: any) => tool.toolIdx === toolIdx,
    );
    const hasToolAnyVisibleCols = selectedTool.columns.some((col: any) =>
      this.isColVisible(toolIdx, col.colIdx),
    );

    if (!hasToolAnyVisibleCols) {
      // @ts-expect-error TS(2339): Property 'tools' does not exist on type 'Readonly<... Remove this comment to see the full error message
      toolIdx = getFirstVisibles(this.props.tools, this.props.hiddenCols)[0];
    }
    return toolIdx !== undefined ? "runset-" + toolIdx : undefined;
  }

  /* Checks whether any of the visible runsets supports a score based plot and adds the score-based option to the
    dropdown if applicable. In case all visible runsets support a score based plot, the score-based quantile plot
    will be set as default. */
  checkForScoreBasedPlot() {
    if (
      // @ts-expect-error TS(2339): Property 'tools' does not exist on type 'Readonly<... Remove this comment to see the full error message
      this.props.tools.some(
        (tool: any) => tool.scoreBased && this.isToolVisible(tool),
      )
    ) {
      this.plotOptions = {
        scoreBased: "Score-based Quantile Plot",
        ...this.plotOptions,
      };
      if (
        // @ts-expect-error TS(2339): Property 'tools' does not exist on type 'Readonly<... Remove this comment to see the full error message
        this.props.tools.every(
          (tool: any) => tool.scoreBased && this.isToolVisible(tool),
        )
      ) {
        this.defaultValues.plot = this.plotOptions.scoreBased;
      }
    }
  }

  isColRelevantForTool = (colIdx: any, toolIdx: any) =>
    this.isColVisible(toolIdx, colIdx) &&
    colIdx.type !== "text" &&
    colIdx.type !== "status";

  isToolRelevantForCol = (tool: any, colName: any) => {
    const colInTool = tool.columns.find(
      (col: any) => col.display_title === colName,
    );
    return (
      this.isToolVisible(tool) &&
      colInTool &&
      this.isColVisible(tool.toolIdx, colInTool.colIdx)
    );
  };

  isColVisibleInAnyTool = (column: any) =>
    // @ts-expect-error TS(2339): Property 'tools' does not exist on type 'Readonly<... Remove this comment to see the full error message
    this.props.tools.some((tool: any) =>
      tool.columns.some(
        (col: any) =>
          col.colIdx === column.colIdx &&
          this.isColVisible(tool.toolIdx, col.colIdx),
      ),
    );

  // Checks whether the given column (defined by its display title) is part of any visible runset that supports a scoring scheme.
  isInVisibleRunsetSupportingScore = (colTitle: any) =>
    // @ts-expect-error TS(2339): Property 'tools' does not exist on type 'Readonly<... Remove this comment to see the full error message
    this.props.tools
      .filter((tool: any) => this.isToolVisible(tool))
      .some(
        (tool: any) =>
          tool.scoreBased &&
          tool.columns.some((col: any) => col.display_title === colTitle),
      );

  isToolVisible = (tool: any) =>
    // @ts-expect-error TS(2339): Property 'hiddenCols' does not exist on type 'Read... Remove this comment to see the full error message
    tool.columns.length !== this.props.hiddenCols[tool.toolIdx].length;

  isColVisible = (toolIdx: any, colIdx: any) =>
    // @ts-expect-error TS(2339): Property 'hiddenCols' does not exist on type 'Read... Remove this comment to see the full error message
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
    // @ts-expect-error TS(2339): Property 'isValue' does not exist on type 'Readonl... Remove this comment to see the full error message
    if (this.state.isValue) {
      // @ts-expect-error TS(2339): Property 'tools' does not exist on type 'Readonly<... Remove this comment to see the full error message
      return this.props.tools
        .filter((tool: any) =>
          // @ts-expect-error TS(2339): Property 'selection' does not exist on type 'Reado... Remove this comment to see the full error message
          this.isToolRelevantForCol(tool, this.state.selection),
        )
        .map(getRunSetName)
        .map((c: any) => {
          return {
            title: c,
            // @ts-expect-error TS(2339): Property 'isInvisible' does not exist on type 'Rea... Remove this comment to see the full error message
            disabled: this.state.isInvisible.some((el: any) => el === c),
            strokeWidth: 4,
          };
        });
    } else {
      // @ts-expect-error TS(2339): Property 'tools' does not exist on type 'Readonly<... Remove this comment to see the full error message
      const tool = this.props.tools[this.state.selection.split("-")[1]];
      // @ts-expect-error TS(2339): Property 'areAllColsHidden' does not exist on type... Remove this comment to see the full error message
      return !this.state.areAllColsHidden
        ? tool.columns
            .filter((col: any) =>
              this.isColRelevantForTool(col.colIdx, tool.toolIdx),
            )
            .map((c: any) => {
              return {
                title: c.display_title,
                // @ts-expect-error TS(2339): Property 'isInvisible' does not exist on type 'Rea... Remove this comment to see the full error message
                disabled: this.state.isInvisible.some(
                  (el: any) => el === c.display_title,
                ),
                strokeWidth: 4,
              };
            })
        : [];
    }
  };

  renderAll = () => {
    // @ts-expect-error TS(2339): Property 'selection' does not exist on type 'Reado... Remove this comment to see the full error message
    const task = this.state.selection;

    // @ts-expect-error TS(2339): Property 'isValue' does not exist on type 'Readonl... Remove this comment to see the full error message
    if (this.state.isValue) {
      /* Option 1: Compare different runsets on one value.
         If the score-based plot is selected, only runsets that support scoring schemes are shown. */
      const tools =
        // @ts-expect-error TS(2339): Property 'plot' does not exist on type 'Readonly<{... Remove this comment to see the full error message
        this.state.plot === this.plotOptions.scoreBased
          // @ts-expect-error TS(2339): Property 'tools' does not exist on type 'Readonly<... Remove this comment to see the full error message
          ? this.props.tools.filter((tool: any) => tool.scoreBased)
          // @ts-expect-error TS(2339): Property 'tools' does not exist on type 'Readonly<... Remove this comment to see the full error message
          : this.props.tools;
      tools.forEach((tool: any) =>
        this.renderData(task, tool.toolIdx, task + tool.toolIdx),
      );
    } else {
      /* Option 2: Compare different values on one runset. */
      // @ts-expect-error TS(2339): Property 'areAllColsHidden' does not exist on type... Remove this comment to see the full error message
      if (!this.state.areAllColsHidden) {
        // @ts-expect-error TS(2339): Property 'selection' does not exist on type 'Reado... Remove this comment to see the full error message
        const index = this.state.selection.split("-")[1];
        // @ts-expect-error TS(2339): Property 'tools' does not exist on type 'Readonly<... Remove this comment to see the full error message
        const tool = this.props.tools[index];
        tool.columns
          .filter(
            (col: any) =>
              this.isColRelevantForTool(col.colIdx, tool.toolIdx) &&
              this.isColVisible(tool.toolIdx, col.colIdx),
          )
          .forEach((column: any) =>
            this.renderData(column.display_title, index, column.display_title),
          );
      }
    }
  };

  renderData = (colTitle: any, toolIdx: any, field: any) => {
    // @ts-expect-error TS(2339): Property 'plot' does not exist on type 'Readonly<{... Remove this comment to see the full error message
    const isPlotScoreBased = this.state.plot === this.plotOptions.scoreBased;
    const isOrdinal = this.handleType() === "ordinal";
    // @ts-expect-error TS(2339): Property 'tools' does not exist on type 'Readonly<... Remove this comment to see the full error message
    const colIdx = this.props.tools[toolIdx].columns.findIndex(
      (value: any) => value.display_title === colTitle,
    );
    let arrayY = [];
    let scoreOfIncorrectResults = 0;

    if (
      // @ts-expect-error TS(2339): Property 'isValue' does not exist on type 'Readonl... Remove this comment to see the full error message
      !this.state.isValue ||
      (colIdx >= 0 && this.isColVisible(toolIdx, colIdx))
    ) {
      // @ts-expect-error TS(2339): Property 'table' does not exist on type 'Readonly<... Remove this comment to see the full error message
      arrayY = this.props.table.map((runSet: any) => {
        // Get y value if it should be shown and normalize it.
        // For correct x values, arrayY needs to have same length as table.
        const runResult = runSet.results[toolIdx];
        let value = null;
        if (
          runResult.category === "correct" ||
          // @ts-expect-error TS(2339): Property 'isResultSelectionDisabled' does not exis... Remove this comment to see the full error message
          (!this.state.isResultSelectionDisabled &&
            // @ts-expect-error TS(2339): Property 'results' does not exist on type 'Readonl... Remove this comment to see the full error message
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
          // @ts-expect-error TS(2339): Property 'getRowName' does not exist on type 'Read... Remove this comment to see the full error message
          rowName: this.props.getRowName(runSet),
          score: runResult.score,
        };
      });

      // @ts-expect-error TS(2339): Property 'plot' does not exist on type 'Readonly<{... Remove this comment to see the full error message
      if (this.state.plot !== this.plotOptions.direct) {
        arrayY = arrayY.filter((dataObj: any) => dataObj.value !== null);
        arrayY = this.sortArray(arrayY, colTitle);
      }
    }

    this.hasInvalidLog = false;
    const newArray: any = [];
    let xPosition = isPlotScoreBased ? scoreOfIncorrectResults : 0;
    arrayY.forEach(({ value, rowName, score }: any) => {
      const isLogAndInvalid =
        // @ts-expect-error TS(2339): Property 'scaling' does not exist on type 'Readonl... Remove this comment to see the full error message
        this.state.scaling === this.scalingOptions.logarithmic && value <= 0;
      xPosition = xPosition + (isPlotScoreBased ? score : 1);

      if (value !== null && !isLogAndInvalid) {
        newArray.push({
          x: xPosition,
          y: value,
          task: rowName,
          // @ts-expect-error TS(2339): Property 'isValue' does not exist on type 'Readonl... Remove this comment to see the full error message
          series: this.state.isValue
            // @ts-expect-error TS(2339): Property 'tools' does not exist on type 'Readonly<... Remove this comment to see the full error message
            ? getRunSetName(this.props.tools[toolIdx])
            : colTitle,
        });
      }

      if (isLogAndInvalid) {
        this.hasInvalidLog = true;
      }
    });
    // @ts-expect-error TS(7053): Element implicitly has an 'any' type because expre... Remove this comment to see the full error message
    this[field] = newArray;
  };

  sortArray = (array: any, column: any) => {
    const currentValue = this.possibleValues.find(
      (value: any) => value.display_title === column,
    );

    // @ts-expect-error TS(2339): Property 'isValue' does not exist on type 'Readonl... Remove this comment to see the full error message
    return this.state.isValue && ["text", "status"].includes(currentValue.type)
      ? array.sort((a: any, b: any) =>
          a.value > b.value ? 1 : b.value > a.value ? -1 : 0,
        )
      : array.sort((a: any, b: any) => +a.value - +b.value);
  };

  setPossibleValues() {
    // @ts-expect-error TS(2339): Property 'tools' does not exist on type 'Readonly<... Remove this comment to see the full error message
    this.props.tools.forEach((tool: any) => {
      tool.columns.forEach((col: any) => {
        if (
          this.isColVisible(tool.toolIdx, col.colIdx) &&
          !this.possibleValues.some(
            (value: any) => value.display_title === col.display_title,
          )
        ) {
          this.possibleValues.push(col);
        }
      });
    });
  }

  renderColumns = () => {
    return this.possibleValues.map((value: any) => {
      const isDisabled =
        // @ts-expect-error TS(2339): Property 'plot' does not exist on type 'Readonly<{... Remove this comment to see the full error message
        this.state.plot === this.plotOptions.scoreBased &&
        !this.isInVisibleRunsetSupportingScore(value.display_title);
      return (
        <option
          key={value.display_title}
          value={value.display_title}
          // @ts-expect-error TS(2322): Type '{ children: any; key: any; value: any; name:... Remove this comment to see the full error message
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

    // @ts-expect-error TS(2339): Property 'isValue' does not exist on type 'Readonl... Remove this comment to see the full error message
    if (this.state.isValue) {
      return (
        // @ts-expect-error TS(2339): Property 'tools' does not exist on type 'Readonly<... Remove this comment to see the full error message
        this.props.tools
          // Cannot use filter() because we need original value of i
          .map((tool: any, i: any) => {
            if (
              // @ts-expect-error TS(2339): Property 'selection' does not exist on type 'Reado... Remove this comment to see the full error message
              !this.isToolRelevantForCol(tool, this.state.selection) ||
              // @ts-expect-error TS(2339): Property 'plot' does not exist on type 'Readonly<{... Remove this comment to see the full error message
              (this.state.plot === this.plotOptions.scoreBased &&
                !tool.scoreBased)
            ) {
              return null;
            }
            // @ts-expect-error TS(2339): Property 'selection' does not exist on type 'Reado... Remove this comment to see the full error message
            const task = this.state.selection;
            // @ts-expect-error TS(7053): Element implicitly has an 'any' type because expre... Remove this comment to see the full error message
            const data = this[task + i];
            const id = getRunSetName(tool);
            this.lineCount++;

            return (
              <LineMarkSeries
                data={data}
                key={id}
                color={color()}
                opacity={this.handleLineState(id)}
                // @ts-expect-error TS(6133): 'event' is declared but its value is never read.
                onValueMouseOver={(datapoint, event) =>
                  this.setState({ value: datapoint })
                }
                // @ts-expect-error TS(6133): 'datapoint' is declared but its value is never rea... Remove this comment to see the full error message
                onValueMouseOut={(datapoint, event) =>
                  this.setState({ value: null })
                }
              />
            );
          })
          .filter((el: any) => !!el)
      );
    // @ts-expect-error TS(2339): Property 'areAllColsHidden' does not exist on type... Remove this comment to see the full error message
    } else if (!this.state.areAllColsHidden) {
      // @ts-expect-error TS(2339): Property 'selection' does not exist on type 'Reado... Remove this comment to see the full error message
      const index = this.state.selection.split("-")[1];
      // @ts-expect-error TS(2339): Property 'tools' does not exist on type 'Readonly<... Remove this comment to see the full error message
      const tool = this.props.tools[index];
      return tool.columns
        .filter((col: any) =>
          this.isColRelevantForTool(col.colIdx, tool.toolIdx),
        )
        .map((column: any) => {
          // @ts-expect-error TS(7053): Element implicitly has an 'any' type because expre... Remove this comment to see the full error message
          const data = this[column.display_title];
          this.lineCount++;

          return (
            <LineMarkSeries
              data={data}
              key={column.display_title}
              color={color()}
              opacity={this.handleLineState(column.display_title)}
              // @ts-expect-error TS(6133): 'event' is declared but its value is never read.
              onValueMouseOver={(datapoint, event) =>
                this.setState({ value: datapoint })
              }
              // @ts-expect-error TS(6133): 'datapoint' is declared but its value is never rea... Remove this comment to see the full error message
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
      // @ts-expect-error TS(2339): Property 'plot' does not exist on type 'Readonly<{... Remove this comment to see the full error message
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
                  // @ts-expect-error TS(2339): Property 'selection' does not exist on type 'Reado... Remove this comment to see the full error message
                  value={this.state.selection}
                  onChange={(ev) =>
                    setURLParameter({ selection: ev.target.value })
                  }
                >
                  <optgroup label="Runsets">
                    // @ts-expect-error TS(2339): Property 'tools' does not exist on type 'Readonly<... Remove this comment to see the full error message
                    {this.props.tools.map((tool: any, i: any) => {
                      const isDisabled =
                        // @ts-expect-error TS(2339): Property 'plot' does not exist on type 'Readonly<{... Remove this comment to see the full error message
                        this.state.plot === this.plotOptions.scoreBased;
                      return this.isToolVisible(tool) ? (
                        <option
                          key={"runset-" + i}
                          value={"runset-" + i}
                          // @ts-expect-error TS(2322): Type '{ children: string; key: string; value: stri... Remove this comment to see the full error message
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
              // @ts-expect-error TS(2554): Expected 6 arguments, but got 4.
              {renderSetting(
                "Plot",
                // @ts-expect-error TS(2339): Property 'plot' does not exist on type 'Readonly<{... Remove this comment to see the full error message
                this.state.plot,
                (ev: any) => setURLParameter({ plot: ev.target.value }),
                this.plotOptions,
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
              {renderSetting(
                "Results",
                // @ts-expect-error TS(2339): Property 'results' does not exist on type 'Readonl... Remove this comment to see the full error message
                this.state.results,
                (ev: any) => setURLParameter({ results: ev.target.value }),
                this.resultsOptions,
                resultsTooltip,
                // @ts-expect-error TS(2339): Property 'isResultSelectionDisabled' does not exis... Remove this comment to see the full error message
                this.state.isResultSelectionDisabled,
              )}
              {renderResetButton(() =>
                setURLParameter({
                  selection: null,
                  plot: null,
                  scaling: null,
                  results: null,
                }),
              )}
            </div>
          </div>
        </div>
        <div>
          <DiscreteColorLegend
            colors={EXTENDED_DISCRETE_COLOR_RANGE}
            items={this.renderLegend()}
            // @ts-expect-error TS(2322): Type '(Object: any, item: any) => void' is not ass... Remove this comment to see the full error message
            onItemClick={(Object: any, item: any) => {
              let line = "";
              line = Object.title.toString();
              // @ts-expect-error TS(2339): Property 'isInvisible' does not exist on type 'Rea... Remove this comment to see the full error message
              if (this.state.isInvisible.indexOf(line) < 0) {
                this.setState({
                  // @ts-expect-error TS(2339): Property 'isInvisible' does not exist on type 'Rea... Remove this comment to see the full error message
                  isInvisible: this.state.isInvisible.concat([line]),
                });
              } else {
                return this.setState({
                  // @ts-expect-error TS(2339): Property 'isInvisible' does not exist on type 'Rea... Remove this comment to see the full error message
                  isInvisible: this.state.isInvisible.filter((l: any) => {
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
  handleLineState = (line: any) => {
    // @ts-expect-error TS(2339): Property 'isInvisible' does not exist on type 'Rea... Remove this comment to see the full error message
    return this.state.isInvisible.indexOf(line) < 0 ? 1 : 0;
  };

  toggleShow = ({ target }: any) => {
    this.setState({
      [target.name]: target.checked,
    });
  };

  handleType = () => {
    // @ts-expect-error TS(2339): Property 'selection' does not exist on type 'Reado... Remove this comment to see the full error message
    const { selection } = this.state;
    const index = this.possibleValues.findIndex(
      (value: any) => value.display_title === selection,
    );
    const type =
      // @ts-expect-error TS(2339): Property 'isValue' does not exist on type 'Readonl... Remove this comment to see the full error message
      this.state.isValue && index >= 0 ? this.possibleValues[index].type : null;
    // @ts-expect-error TS(2339): Property 'isValue' does not exist on type 'Readonl... Remove this comment to see the full error message
    return this.state.isValue && (type === "text" || type === "status")
      ? "ordinal"
      // @ts-expect-error TS(2339): Property 'scaling' does not exist on type 'Readonl... Remove this comment to see the full error message
      : this.state.scaling === this.scalingOptions.linear
      ? "linear"
      : "log";
  };

  render() {
    this.setPossibleValues();
    this.renderAll();
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
    return (
      <div className="quantilePlot">
        // @ts-expect-error TS(2339): Property 'areAllColsHidden' does not exist on type... Remove this comment to see the full error message
        {!this.state.areAllColsHidden && this.renderAllSettings()}
        // @ts-expect-error TS(2769): No overload matches this call.
        <Plot
          margin={{ left: 90 }}
          yType={this.handleType()}
          {...plotDimensions}
        >
          <VerticalGridLines />
          <HorizontalGridLines />
          <XAxis tickFormat={(value) => value} />
          <YAxis tickFormat={(value) => value} />
          // @ts-expect-error TS(2339): Property 'value' does not exist on type 'Readonly<... Remove this comment to see the full error message
          {this.state.value ? <Hint value={this.state.value} /> : null}
          {this.renderLines()}
        </Plot>
        // @ts-expect-error TS(2339): Property 'areAllColsHidden' does not exist on type... Remove this comment to see the full error message
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
