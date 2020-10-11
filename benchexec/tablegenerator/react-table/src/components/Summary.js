// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import React from "react";
import ReactTable from "react-table";
import "react-table/react-table.css";
import equals from "deep-equal";
import withFixedColumns from "react-table-hoc-fixed-columns";
import "react-table-hoc-fixed-columns/lib/styles.css";
import {
  createRunSetColumns,
  StandardColumnHeader,
  SelectColumnsButton,
} from "./TableComponents.js";
import { determineColumnWidth, isNumericColumn, isNil } from "../utils/utils";
import { buildFormatter, processData } from "../utils/stats.js";

const ReactTableFixedColumns = withFixedColumns(ReactTable);

const isTestEnv = process.env.NODE_ENV === "test";

export default class Summary extends React.PureComponent {
  constructor(props) {
    super(props);

    this.skipStats = isTestEnv && !props.onStatsReady;

    this.state = {
      fixed: true,
      stats: props.stats,
    };
    this.infos = [
      "displayName",
      "tool",
      "limit",
      "host",
      "os",
      "system",
      "date",
      "runset",
      "branch",
      "options",
      "property",
    ];
    this.headerWidth = window.innerWidth * 0.15;
    this.width = window.innerWidth;
  }

  renderTooltip = (cell) =>
    Object.keys(cell)
      .filter((key) => cell[key] && key !== "sum")
      .map(
        (key) => `${key}: ${cell[key].replace(/(&#x2007;)|(&#x2008;)/g, "")}`,
      )
      .join(", ") || undefined;

  //fix columns
  handleInputChange = ({ target }) => {
    this.setState({
      [target.name]: target.checked,
    });
  };

  renderEnvironmentRow = (row, text, colSpan, j) => {
    if (row === "options") {
      return (
        <td
          colSpan={colSpan}
          key={text + j}
          className="header__tool-row options"
        >
          <ul>{this.renderOptions(text)}</ul>
        </td>
      );
    }
    return (
      <td colSpan={colSpan} key={text + j} className="header__tool-row">
        {text}{" "}
      </td>
    );
  };
  renderOptions = (text) => {
    return text.split(/[\s]+-/).map((option, i) => (
      <li key={option}>
        <code>{i === 0 ? option : `-${option}`}</code>
      </li>
    ));
  };

  createRowTitleColumn = () => ({
    Header: () => (
      <div className="toolsHeader">
        <form>
          <label title="Fix the first column">
            Fixed row title:
            <input
              id="fixed-row-title"
              name="fixed"
              type="checkbox"
              checked={this.state.fixed}
              onChange={this.handleInputChange}
            />
          </label>
        </form>
      </div>
    ),
    fixed: this.state.fixed ? "left" : "",
    minWidth: this.headerWidth,
    columns: [
      {
        id: "summary",
        minWidth: this.headerWidth,
        Header: <SelectColumnsButton handler={this.props.selectColumn} />,
        accessor: "",
        Cell: (cell) => (
          <div
            dangerouslySetInnerHTML={{ __html: cell.value.title }}
            title={cell.value.description}
            className="row-title"
          />
        ),
      },
    ],
  });

  componentDidMount() {
    this.updateStats();
  }

  componentDidUpdate(prevProps) {
    if (!equals(prevProps.data, this.props.data)) {
      this.updateStats();
    }
  }

  createColumn = (runSetIdx, column, columnIdx) => ({
    id: `${runSetIdx}_${column.display_title}_${columnIdx}`,
    Header: (
      <StandardColumnHeader
        column={column}
        className="columns"
        title="Show Quantile Plot of this column"
        onClick={(e) => this.props.changeTab(e, column, 2)}
      />
    ),
    show:
      !this.props.hiddenCols[runSetIdx].includes(columnIdx) &&
      (isNumericColumn(column) || column.type === "status"),
    minWidth: determineColumnWidth(
      column,
      null,
      column.type === "status" ? 6 : null,
    ),
    accessor: (row) => row.content[runSetIdx][columnIdx],
    Cell: (cell) =>
      !isNil(cell.value) ? (
        <div
          dangerouslySetInnerHTML={{
            __html: Number.isInteger(cell.value.sum)
              ? Number(cell.value.sum)
              : cell.value.sum,
          }}
          className="cell"
          title={
            column.type !== "status"
              ? this.renderTooltip(cell.value)
              : undefined
          }
        ></div>
      ) : (
        <div className="cell">-</div>
      ),
  });

  transformStatsFromWorkers(stats) {
    // our stats template to steal from

    const selector = {
      0: "total",
      2: "correct-total",
      3: "correct-true",
      4: "correct-false",
      5: "wrong-total",
      6: "wrong-true",
      7: "wrong-false",
    };
    const templ = this.state.stats;

    const transformed = templ.map((row, rowIdx) => {
      row.content = row.content.map((tool, toolIdx) => {
        const key = selector[rowIdx];
        if (!key || !stats[toolIdx]) {
          return tool;
        }
        return stats[toolIdx].map((col) => col[key]);
      });
      return row;
    });

    this.setState({
      stats: transformed,
      statUpdateCycle: this.state.statUpdateCycle + 1,
    });
  }

  async updateStats(oldStats) {
    const { tools, data: table, onStatsReady } = this.props;
    const formatter = buildFormatter(this.props.tools);
    let res = this.skipStats
      ? {}
      : await processData({ tools, table, formatter });

    // fill up stat array to match column mapping

    res = res.map((tool, toolIdx) => {
      const out = [];
      const toolColumns = this.props.tools[toolIdx].columns;
      let pointer = 0;
      let curr = toolColumns[pointer];

      for (const col of tool) {
        const { title } = col;
        while (pointer < toolColumns.length && title !== curr.title) {
          out.push({});
          pointer++;
          curr = toolColumns[pointer];
        }
        if (pointer >= toolColumns.length) {
          break;
        }
        out.push(col);
        pointer++;
        curr = toolColumns[pointer];
      }

      return out;
    });

    this.transformStatsFromWorkers(res);

    if (onStatsReady) {
      console.log("calling onStatsReady");
      onStatsReady();
    } else {
      console.log("onStatsReady not found");
    }
  }

  render() {
    const statColumns = this.props.tools
      .map((runSet, runSetIdx) =>
        createRunSetColumns(runSet, runSetIdx, this.createColumn),
      )
      .flat();

    return (
      <div id="summary">
        <div id="benchmark_setup">
          <h2>Benchmark Setup</h2>
          <table>
            <tbody>
              {this.infos
                .map((row) => this.props.tableHeader[row])
                .filter((row) => row !== null)
                .map((row, i) => (
                  <tr key={"tr-" + row.id} className={row.id}>
                    <th key={"td-" + row.id}>{row.name}</th>
                    {row.content.map((tool, j) =>
                      this.renderEnvironmentRow(row.id, tool[0], tool[1], j),
                    )}
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
        <div id="statistics">
          <h2>Statistics</h2>
          <ReactTableFixedColumns
            data={this.state.stats}
            columns={[this.createRowTitleColumn()].concat(statColumns)}
            showPagination={false}
            className="-highlight"
            minRows={0}
            sortable={false}
            width={this.width}
          />
        </div>
        <p>
          Generated by{" "}
          <a
            className="link"
            href="https://github.com/sosy-lab/benchexec"
            target="_blank"
            rel="noopener noreferrer"
          >
            {" "}
            BenchExec {this.props.version}
          </a>
        </p>
      </div>
    );
  }
}
