// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import React from "react";
import { HashRouter as Router, Switch, Route, Link } from "react-router-dom";
import Table from "./ReactTable.js";
import Summary from "./Summary.js";
import Info from "./Info.js";
import SelectColumn from "./SelectColumn.js";
import ScatterPlot from "./ScatterPlot.js";
import QuantilePlot from "./QuantilePlot.js";
import LinkOverlay from "./LinkOverlay.js";
import Reset from "./Reset.js";
import { prepareTableData } from "../utils/utils";
import classNames from "classnames";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faQuestionCircle } from "@fortawesome/free-solid-svg-icons";
import { createHiddenColsFromURL } from "../utils/utils";

const menuItems = [
  { key: "summary", title: "Summary", path: "/" },
  { key: "table", title: "Table", path: "/table" },
  { key: "quantile", title: "Quantile Plot", path: "/quantile" },
  { key: "scatter", title: "Scatter Plot", path: "/scatter" },
  {
    key: "info",
    title: "Info",
    path: "/info",
    icon: <FontAwesomeIcon icon={faQuestionCircle} />,
  },
];

const getCurrentPath = () => document.location.hash.split("?")[0].substr(1);

export default class Overview extends React.Component {
  constructor(props) {
    super(props);
    //imported data
    const { tableHeader, tools, columns, table, stats } = prepareTableData(
      props.data,
    );

    this.originalTable = table;
    this.originalTools = tools;

    this.columns = columns;
    this.stats = stats;
    this.tableHeader = tableHeader;

    this.filteredData = [];

    //data is handled and changed here; To use it in other components hand it over with component
    //To change data in component (e.g. filter): function to change has to be in overview
    this.state = {
      tools,
      table,

      showSelectColumns: false,
      showLinkOverlay: false,
      filtered: [],
      tabIndex: 0,

      active: (
        menuItems.find((i) => i.path === getCurrentPath()) || { key: "summary" }
      ).key,

      quantilePreSelection: tools[0].columns[1],
      hiddenCols: createHiddenColsFromURL(tools),
    };
  }

  componentDidMount() {
    window.addEventListener("popstate", this.updateHiddenCols, false);
  }

  componentWillUnmount() {
    window.removeEventListener("popstate", this.updateHiddenCols, false);
  }

  updateHiddenCols = () => {
    this.setState({ hiddenCols: createHiddenColsFromURL(this.state.tools) });
  };

  // -----------------------SelectColumns-----------------------
  toggleSelectColumns = (ev) => {
    ev.stopPropagation();

    this.setState((prevState) => ({
      showSelectColumns: !prevState.showSelectColumns,
    }));
  };

  // -----------------------Link Overlay-----------------------
  toggleLinkOverlay = (ev, hrefRow) => {
    ev.preventDefault();

    this.setState((prevState) => ({
      showLinkOverlay: !prevState.showLinkOverlay,
      link: hrefRow,
    }));
  };

  // -----------------------Filter-----------------------
  setFilter = (filteredData) => {
    this.filteredData = filteredData.map((row) => {
      return row._original;
    });
  };
  filterPlotData = (filter) => {
    this.setState({
      table: this.filteredData,
      filtered: filter,
    });
  };
  resetFilters = () => {
    this.setState({
      table: this.originalTable,
      filtered: [],
    });
  };

  // -----------------------Common Functions-----------------------
  getRowName = (row) => row.id.filter((s) => s).join(" | ");

  changeTab = (_, column, tab) => {
    this.setState({
      tabIndex: tab,
      quantilePreSelection: column,
    });
  };

  render() {
    let urlParams = document.location.href.split("?")[1] || "";
    urlParams = urlParams
      .split("&")
      .filter((param) => param.startsWith("hidden"))
      .join("&");
    return (
      <Router>
        <div className="overview">
          <div className="overview-container">
            <div className="menu">
              {menuItems.map(({ key, title, path, icon }) => (
                <Link
                  className={classNames("menu-item", {
                    selected: this.state.active === key,
                  })}
                  to={path + (urlParams ? "?" + urlParams : "")}
                  key={path}
                  onClick={() => this.setState(() => ({ active: key }))}
                >
                  {title} {icon || ""}
                </Link>
              ))}
              <Reset
                isFiltered={!!this.state.filtered.length}
                resetFilters={this.resetFilters}
                filteredCount={this.state.table.length}
                totalCount={this.originalTable.length}
              />
            </div>
            <div className="route-container">
              <Switch>
                <Route exact path="/">
                  <Summary
                    tools={this.state.tools}
                    tableHeader={this.tableHeader}
                    version={this.props.data.version}
                    selectColumn={this.toggleSelectColumns}
                    stats={this.stats}
                    changeTab={this.changeTab}
                    hiddenCols={this.state.hiddenCols}
                  />
                </Route>
                <Route path="/table">
                  <Table
                    tableHeader={this.tableHeader}
                    data={this.originalTable}
                    tools={this.state.tools}
                    selectColumn={this.toggleSelectColumns}
                    setFilter={this.setFilter}
                    filterPlotData={this.filterPlotData}
                    filtered={this.state.filtered}
                    toggleLinkOverlay={this.toggleLinkOverlay}
                    changeTab={this.changeTab}
                    hiddenCols={this.state.hiddenCols}
                  />
                </Route>
                <Route path="/quantile">
                  <QuantilePlot
                    table={this.state.table}
                    tools={this.state.tools}
                    preSelection={this.state.quantilePreSelection}
                    getRowName={this.getRowName}
                    hiddenCols={this.state.hiddenCols}
                  />
                </Route>
                <Route path="/scatter">
                  <ScatterPlot
                    table={this.state.table}
                    columns={this.columns}
                    tools={this.state.tools}
                    getRowName={this.getRowName}
                    hiddenCols={this.state.hiddenCols}
                  />
                </Route>
                <Route path="/info">
                  <Info
                    version={this.props.data.version}
                    selectColumn={this.toggleSelectColumns}
                  />
                </Route>
              </Switch>
            </div>
          </div>
          <div>
            {this.state.showSelectColumns && (
              <SelectColumn
                close={this.toggleSelectColumns}
                currColumns={this.columns}
                tableHeader={this.tableHeader}
                tools={this.state.tools}
                hiddenCols={this.state.hiddenCols}
              />
            )}
            {this.state.showLinkOverlay && (
              <LinkOverlay
                close={this.toggleLinkOverlay}
                link={this.state.link}
                toggleLinkOverlay={this.toggleLinkOverlay}
              />
            )}
          </div>
        </div>
      </Router>
    );
  }
}
