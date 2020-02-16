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
  LineMarkSeries,
  VerticalGridLines,
  HorizontalGridLines,
  XAxis,
  YAxis,
  DiscreteColorLegend,
  Hint
} from "react-vis";
import {
  getRunSetName,
  EXTENDED_DISCRETE_COLOR_RANGE,
  setParam,
  getHashSearch
} from "../utils/utils";

export default class QuantilePlot extends React.Component {
  constructor(props) {
    super(props);

    const queryProps = getHashSearch();

    const { metric, quantileRaw, linearRaw, correctRaw } = queryProps;

    const quantile = Boolean(quantileRaw);
    const linear = Boolean(linearRaw);
    const correct = Boolean(correctRaw);

    const parameterSelection = metric
      ? this.props.tools
          .map(tool => tool.columns)
          .flat()
          .find(col => col.display_title === metric)
      : this.props.preSelection;

    const visibleColumn = parameterSelection.isVisible
      ? parameterSelection
      : this.props.tools
          .map(tool => tool.columns)
          .flat()
          .some(col => col.isVisible);

    // TODO: deselect all tools => open quantiles => BOOOOOOMMMM
    this.state = {
      selection: visibleColumn && visibleColumn.display_title,
      quantile: typeof quantile === "boolean" ? quantile : true,
      linear: typeof linear === "boolean" ? linear : false,
      correct: typeof correct === "boolean" ? correct : true,
      isValue: true, //two versions of plot: one Value more RunSets => isValue:true; oneRunSet more Values => isValue:false
      isInvisible: []
    };

    this.possibleValues = [];
    this.lineCount = 1;
  }

  static relevantColumn = column =>
    column.isVisible && column.type !== "text" && column.type !== "status";

  relevantRunSet = tool =>
    tool.isVisible &&
    tool.columns.some(c => c.display_title === this.state.selection);

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
      height: window.innerHeight
    });
  };

  // --------------------rendering-----------------------------
  renderLegend = () => {
    if (this.state.isValue) {
      return this.props.tools.filter(this.relevantRunSet).map(getRunSetName);
    } else {
      return this.props.tools[this.state.selection.split("-")[1]].columns
        .filter(QuantilePlot.relevantColumn)
        .map(c => c.display_title);
    }
  };

  renderAll = () => {
    const task = this.state.selection;

    if (this.state.isValue) {
      //var 1: compare different RunSets on one value
      this.props.tools.forEach((tool, i) => this.renderData(task, i, task + i));
    } else {
      //var 2: compare different values of one RunSet
      const index = this.state.selection.split("-")[1];
      this.props.tools[index].columns
        .filter(QuantilePlot.relevantColumn)
        .forEach(column =>
          this.renderData(column.display_title, index, column.display_title)
        );
    }
  };

  renderData = (column, tool, field) => {
    const isOrdinal = this.handleType() === "ordinal";
    let arrayY = [];
    const index = this.props.tools[tool].columns.findIndex(
      value => value.display_title === column
    );

    if (!this.state.isValue || index >= 0) {
      arrayY = this.props.table.map(runSet => {
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
        arrayY = arrayY.filter(element => element[0] !== null);
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
          info: el[1]
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
      value => value.display_title === column
    );

    return this.state.isValue && ["text", "status"].includes(currentValue.type)
      ? array.sort((a, b) => (a[0] > b[0] ? 1 : b[0] > a[0] ? -1 : 0))
      : array.sort((a, b) => +a[0] - +b[0]);
  };

  renderColumns = () => {
    this.props.tools.forEach(tool => {
      tool.columns.forEach(column => {
        if (
          column.isVisible &&
          !this.possibleValues.some(
            value => value.display_title === column.display_title
          )
        ) {
          this.possibleValues.push(column);
        }
      });
    });
    this.renderAll();
    return this.possibleValues.map(value => {
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
        .filter(el => !!el);
    } else {
      const index = this.state.selection.split("-")[1];

      return this.props.tools[index].columns
        .filter(QuantilePlot.relevantColumn)
        .map(column => {
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

  // ------------------------handeling----------------------------
  handleLineState = line => {
    return this.state.isInvisible.indexOf(line) < 0 ? 1 : 0;
  };

  handleColumn = ev => {
    setParam({ metric: ev.target.value });
    this.setState({
      selection: ev.target.value,
      isValue: this.props.tools.some(tool =>
        tool.columns.some(value => value.display_title === ev.target.value)
      )
    });
  };
  toggleQuantile = () => {
    setParam({ quantile: !this.state.quantile });
    this.setState(prevState => ({
      quantile: !prevState.quantile
    }));
  };
  toggleCorrect = () => {
    setParam({ correct: !this.state.correct });
    this.setState(prevState => ({
      correct: !prevState.correct
    }));
  };
  toggleLinear = () => {
    setParam({ linear: !this.state.linear });
    this.setState(prevState => ({
      linear: !prevState.linear
    }));
  };
  toggleShow = ({ target }) => {
    this.setState({
      [target.name]: target.checked
    });
  };

  handleType = () => {
    const { selection } = this.state;
    const index = this.possibleValues.findIndex(
      value => value.display_title === selection
    );
    const type = this.state.isValue ? this.possibleValues[index].type : null;

    return this.state.isValue && (type === "text" || type === "status")
      ? "ordinal"
      : this.state.linear
      ? "linear"
      : "log";
  };

  render() {
    return (
      <div className="quantilePlot">
        <select
          name="Select Column"
          value={this.state.selection}
          onChange={this.handleColumn}
        >
          <optgroup label="Run sets">
            {this.props.tools.map((runset, i) => {
              return runset.isVisible ? (
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
        <XYPlot
          height={window.innerHeight - 200}
          width={window.innerWidth - 100}
          margin={{ left: 90 }}
          yType={this.handleType()}
        >
          <VerticalGridLines />
          <HorizontalGridLines />
          <XAxis tickFormat={value => value} />
          <YAxis tickFormat={value => value} />
          {this.state.value ? <Hint value={this.state.value} /> : null}
          <DiscreteColorLegend
            colors={EXTENDED_DISCRETE_COLOR_RANGE}
            items={this.renderLegend()}
            onItemClick={(Object, item) => {
              let line = "";
              line = Object.toString();
              if (this.state.isInvisible.indexOf(line) < 0) {
                this.setState({
                  isInvisible: this.state.isInvisible.concat([line])
                });
              } else {
                return this.setState({
                  isInvisible: this.state.isInvisible.filter(l => {
                    return l !== line;
                  })
                });
              }
            }}
          />
          {this.renderLines()}
        </XYPlot>
        {this.lineCount === 0 && (
          <div className="plot__noresults">
            {this.hasInvalidLog
              ? "All results have undefined values"
              : "No correct results"}
          </div>
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
