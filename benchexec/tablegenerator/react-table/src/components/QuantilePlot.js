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
} from "react-vis";
import {
  getRunSetName,
  EXTENDED_DISCRETE_COLOR_RANGE,
  setParam,
  getHashSearch,
  stringAsBoolean,
  getFirstVisibles,
} from "../utils/utils";

const defaultValues = {
  quantile: "true",
  linear: "false",
  correct: "true",
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

    let { selection, quantile, linear, correct } = {
      ...defaultValues,
      ...queryProps,
    };

    quantile = stringAsBoolean(quantile);
    linear = stringAsBoolean(linear);
    correct = stringAsBoolean(correct);

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
      selection: selection,
      quantile: quantile,
      linear: linear,
      correct: correct,
      isValue: isValue, //two versions of plot: one Value more RunSets => isValue:true; oneRunSet more Values => isValue:false
      isInvisible: [],
      areAllColsHidden: selection === undefined,
    };
  }

  relevantColumn = (column) =>
    this.isColVisibleInAnyTool(column) &&
    column.type !== "text" &&
    column.type !== "status";

  relevantRunSet = (tool) =>
    tool.columns.length !== this.props.hiddenCols[tool.toolIdx].length &&
    tool.columns.some((c) => c.display_title === this.state.selection);

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
        .filter(this.relevantRunSet)
        .map(getRunSetName)
        .map((c) => {
          return {
            title: c,
            disabled: this.state.isInvisible.some((el) => el === c),
          };
        });
    } else {
      return !this.state.areAllColsHidden
        ? this.props.tools[this.state.selection.split("-")[1]].columns
            .filter((col) => this.relevantColumn(col))
            .map((c) => {
              return {
                title: c.display_title,
                disabled: this.state.isInvisible.some(
                  (el) => el === c.display_title,
                ),
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
        this.props.tools[index].columns
          .filter((col) => this.relevantColumn(col))
          .forEach((column) =>
            this.renderData(column.display_title, index, column.display_title),
          );
      }
    }
  };

  renderData = (column, tool, field) => {
    const isOrdinal = this.handleType() === "ordinal";
    let arrayY = [];
    const index = this.props.tools[tool].columns.findIndex(
      (value) => value.display_title === column,
    );

    if (!this.state.isValue || index >= 0) {
      arrayY = this.props.table.map((runSet) => {
        // Get y value if it should be shown and normalize it.
        // For correct x values, arrayY needs to have same length as table.
        const runResult = runSet.results[tool];
        let value = null;
        if (!this.state.correct || runResult.category === "correct") {
          value = runResult.values[index].raw;
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

      if (this.state.quantile) {
        arrayY = arrayY.filter((element) => element[0] !== null);
        arrayY = this.sortArray(arrayY, column);
      }
    }

    this.hasInvalidLog = false;
    const newArray = [];

    arrayY.forEach((el, i) => {
      const value = el[0];
      const isLogAndInvalid = !this.state.linear && value <= 0;

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
          if (!this.relevantRunSet(tool)) {
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
        return this.props.tools[index].columns
          .filter((col) => this.relevantColumn(col))
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
  // ------------------------handeling----------------------------
  handleLineState = (line) => {
    return this.state.isInvisible.indexOf(line) < 0 ? 1 : 0;
  };

  handleColumn = (ev) => {
    setParam({ selection: ev.target.value });
  };
  toggleQuantile = () => {
    setParam({ quantile: !this.state.quantile });
  };
  toggleCorrect = () => {
    setParam({ correct: !this.state.correct });
  };
  toggleLinear = () => {
    setParam({ linear: !this.state.linear });
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
      : this.state.linear
      ? "linear"
      : "log";
  };

  render() {
    return (
      <div className="quantilePlot">
        {!this.state.areAllColsHidden && (
          <select
            name="Select Column"
            value={this.state.selection}
            onChange={this.handleColumn}
          >
            <optgroup label="Run sets">
              {this.props.tools.map((runset, i) => {
                return runset.columns.length !==
                  this.props.hiddenCols[runset.toolIdx].length ? (
                  <option
                    key={"runset-" + i}
                    value={"runset-" + i}
                    name={"runset-" + i}
                  >
                    {getRunSetName(runset)}
                  </option>
                ) : null;
              })}
            </optgroup>
            <optgroup label="Columns">{this.renderColumns()}</optgroup>
          </select>
        )}
        <XYPlot
          height={window.innerHeight - 200}
          width={window.innerWidth - 100}
          margin={{ left: 90 }}
          yType={this.handleType()}
        >
          <VerticalGridLines />
          <HorizontalGridLines />
          <XAxis tickFormat={(value) => value} />
          <YAxis tickFormat={(value) => value} />
          {this.state.value ? <Hint value={this.state.value} /> : null}
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
          {this.renderLines()}
        </XYPlot>
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
        <button className="btn" onClick={this.toggleQuantile}>
          {this.state.quantile
            ? "Switch to Direct Plot"
            : "Switch to Quantile Plot"}
        </button>
        <button className="btn" onClick={this.toggleLinear}>
          {this.state.linear
            ? "Switch to Logarithmic Scale"
            : "Switch to Linear Scale"}
        </button>
        <button className="btn" onClick={this.toggleCorrect}>
          {this.state.correct
            ? "Switch to All Results"
            : "Switch to Correct Results Only"}
        </button>
      </div>
    );
  }
}
