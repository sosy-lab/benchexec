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

export default class Overlay extends React.Component {
  constructor(props) {
    super(props);

    const visibleColumn = this.props.preSelection.isVisible
      ? this.props.preSelection
      : this.props.tools
          .map(tool => tool.columns)
          .flat()
          .find(col => col.isVisible);

    // TODO: deselect all tools => open quantiles => BOOOOOOMMMM
    this.state = {
      selection: visibleColumn && visibleColumn.display_title,
      quantile: true,
      linear: false,
      correct: true,
      isValue: true, //two versions of plot: one Value more RunSets => isValue:true; oneRunSet more Values => isValue:false
      isInvisible: []
    };

    this.possibleValues = [];
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
      height: window.innerHeight
    });
  };
  // --------------------rendering-----------------------------
  renderLegend = () => {
    return this.state.isValue
      ? this.props.tools
          .filter(t => t.isVisible)
          .map(tool => this.props.getRunSets(tool))
      : this.props.tools[this.state.selection.split("-")[1]].columns
          .map(c =>
            c.isVisible && c.type !== "text" && c.type !== "status"
              ? c.display_title
              : null
          )
          .filter(Boolean);
  };

  renderAll = () => {
    const task = this.state.selection;

    if (this.state.isValue) {
      //var 1: compare different RunSets on one value
      this.props.tools.forEach((tool, i) => {
        this.renderData(this.props.table, task, i, task + i);
      });
    } else {
      //var 2: compare different values of one RunSet
      const index = this.state.selection.split("-")[1];
      this.props.tools[index].columns.forEach(column => {
        if (
          !(column.type === "status" || column.type === "text") &&
          column.isVisible
        ) {
          this.renderData(
            this.props.table,
            column.display_title,
            index,
            column.display_title
          );
        }
      });
    }
  };

  renderData = (rows, column, tool, field) => {
    let arrayY = [];
    const index = this.props.tools[tool].columns.findIndex(
      value => value.display_title === column
    );

    if (!this.state.isValue || index >= 0) {
      const relevantRows = this.state.correct
        ? rows.filter(rs => rs.results[tool].category === "correct")
        : rows;

      arrayY = relevantRows.map(runSet => [
        runSet.results[tool].values[index].raw,
        runSet.short_filename
      ]);

      if (this.state.quantile) {
        arrayY = this.sortArray(arrayY, column);
      }
    }

    this.hasInvalidLog = false;
    const newArray = [];
    const isOrdinal = this.handleType() === "ordinal";

    arrayY.forEach((el, i) => {
      const value = el[0];
      const isLogAndInvalid = !this.state.linear && value <= 0;

      if (value !== null && !isLogAndInvalid) {
        newArray.push({
          x: i + 1,
          y: isOrdinal ? value : +value,
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
          this.possibleValues.findIndex(
            value => value.display_title === column.display_title
          ) < 0
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

    if (this.state.isValue) {
      return this.props.tools
        .map((tool, i) => {
          const task = this.state.selection;
          const data = this[task + i];

          if (data && data.length > 0) {
            this.lineCount++;
          }

          return tool.isVisible ? (
            <LineMarkSeries
              data={data}
              key={tool.benchmarkname + tool.date}
              opacity={this.handleLineState(this.props.getRunSets(tool))}
              onValueMouseOver={(datapoint, event) =>
                this.setState({ value: datapoint })
              }
              onValueMouseOut={(datapoint, event) =>
                this.setState({ value: null })
              }
            />
          ) : null;
        })
        .filter(el => !!el);
    } else {
      const index = this.state.selection.split("-")[1];

      return this.props.tools[index].columns
        .map((column, i) => {
          const data = column.isVisible ? this[column.display_title] : null;

          if (data && data.length > 0) {
            this.lineCount++;
          }

          return data && column.type !== "text" && column.type !== "status" ? (
            <LineMarkSeries
              data={data}
              key={column.display_title}
              opacity={this.handleLineState(column.display_title)}
              onValueMouseOver={(datapoint, event) =>
                this.setState({ value: datapoint })
              }
              onValueMouseOut={(datapoint, event) =>
                this.setState({ value: null })
              }
            />
          ) : null;
        })
        .filter(el => !!el);
    }
  };

  // ------------------------handeling----------------------------
  handleLineState = line => {
    return this.state.isInvisible.indexOf(line) < 0 ? 1 : 0;
  };

  handleColumn = ev => {
    this.setState({
      selection: ev.target.value,
      isValue:
        this.props.tools
          .map(
            tool =>
              tool.columns.findIndex(
                value => value.display_title === ev.target.value
              ) >= 0
          )
          .findIndex(value => value === true) >= 0
    });
  };
  toggleQuantile = () => {
    this.setState(prevState => ({
      quantile: !prevState.quantile
    }));
  };
  toggleCorrect = () => {
    this.setState(prevState => ({
      correct: !prevState.correct
    }));
  };
  toggleLinear = () => {
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
                  {this.props.getRunSets(runset, i)}
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
