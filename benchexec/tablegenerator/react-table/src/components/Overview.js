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
import FilterBox from "./FilterBox/FilterBox.js";
import LinkOverlay from "./LinkOverlay.js";
import classNames from "classnames";
import FilterInfoButton from "./FilterInfoButton.js";
import {
  prepareTableData,
  getRawOrDefault,
  getTaskIdParts,
} from "../utils/utils";
import {
  getFilterableData,
  buildMatcher,
  applyMatcher,
} from "../utils/filters";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faQuestionCircle } from "@fortawesome/free-solid-svg-icons";
import {
  createHiddenColsFromURL,
  makeUrlFilterDeserializer,
  makeUrlFilterSerializer,
  setConstantHashSearch,
} from "../utils/utils";
import deepEqual from "deep-equal";

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

const getActiveTab = () =>
  (
    menuItems.find(
      (i) => i.path === document.location.hash.split("?")[0].substr(1),
    ) || { key: "summary" }
  ).key;

export default class Overview extends React.Component {
  constructor(props) {
    super(props);
    //imported data
    const {
      tableHeader,
      taskIdNames,
      tools,
      columns,
      table,
      stats,
      initial,
    } = prepareTableData(props.data);

    if (initial && !document.location.href.includes("#")) {
      setConstantHashSearch(initial);
    }

    const filterable = getFilterableData(this.props.data);
    this.originalTable = table;
    this.originalTools = tools;

    this.taskIdNames = taskIdNames;

    this.columns = columns;
    this.stats = stats;
    this.tableHeader = tableHeader;

    this.filteredData = [];

    this.routerRef = React.createRef();

    //data is handled and changed here; To use it in other components hand it over with component
    //To change data in component (e.g. filter): function to change has to be in overview
    this.state = {
      tools,
      table,
      filterable,
      showSelectColumns: false,
      showLinkOverlay: false,
      filtered: [],
      tabIndex: 0,
      filterBoxVisible: false,
      active: getActiveTab(),
      quantilePreSelection: tools[0].columns[1],
      hiddenCols: createHiddenColsFromURL(tools),
    };
    // Collect all status and category values for filter drop-down
    this.statusValues = this.findAllValuesOfColumn(
      (_tool, column) => column.type === "status",
      (_runResult, value) => getRawOrDefault(value),
    );
    this.categoryValues = this.findAllValuesOfColumn(
      (_tool, column) => column.type === "status",
      (runResult, _value) => runResult.category,
    );

    const categoryValuesWithTrailingSpace = this.categoryValues.map(
      (tool) =>
        tool &&
        tool.map((column) => column && column.map((item) => `${item} `)),
    );

    this.filterUrlSetter = makeUrlFilterSerializer(
      this.statusValues,
      categoryValuesWithTrailingSpace,
    );

    this.filterUrlRetriever = makeUrlFilterDeserializer(
      this.statusValues,
      categoryValuesWithTrailingSpace,
    );

    const deserializedFilters = this.getFiltersFromUrl();
    if (deserializedFilters) {
      this.filteredData = this.runFilter(deserializedFilters);
      this.lastFiltered = deserializedFilters;
      this.state = {
        ...this.state,
        table: this.filteredData,
        filtered: deserializedFilters,
      };
    }
  }

  componentDidMount() {
    this.removeHistoryListener = this.routerRef.current.history.listen(
      (_, action) => {
        this.updateState();
        if (action === "POP") {
          this.updateFiltersFromUrl();
        }
      },
    );
  }

  componentWillUnmount() {
    this.removeHistoryListener();
  }

  getFiltersFromUrl = () => {
    const deserializedFilters = this.filterUrlRetriever() || [];
    if (!deepEqual(this.lastFiltered, deserializedFilters)) {
      // we only want to kick off filtering when filters changed
      return deserializedFilters;
    }
    return null;
  };

  updateFiltersFromUrl = () => {
    const newFilters = this.getFiltersFromUrl();
    if (newFilters) {
      this.filteredData = this.runFilter(newFilters);
      this.setState({
        table: this.filteredData,
        filtered: newFilters,
      });
      this.lastFiltered = newFilters;
    }
  };

  updateState = () =>
    this.setState({
      active: getActiveTab(),
      hiddenCols: createHiddenColsFromURL(this.state.tools),
    });

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
  setFilter = (filteredData, raw = false) => {
    if (raw) {
      this.filteredData = filteredData;
      return;
    }
    this.filteredData = filteredData.map((row) => {
      return row._original;
    });
  };

  runFilter(filter) {
    const matcher = buildMatcher(filter);
    return applyMatcher(matcher)(this.originalTable);
  }

  filterPlotData = (filter, runFilterLogic = true) => {
    // updating url filters on next tick to ensure that state is already set
    // when handler is called);
    if (this.lastImmediate) {
      clearImmediate(this.lastImmediate);
    }
    this.lastImmediate = setImmediate(() => {
      this.filterUrlSetter(filter, { history: this.routerRef.current.history });
      this.lastFiltered = filter.filter(
        (item) => (item.values && item.values.length > 0) || item.value,
      );
    });
    if (runFilterLogic) {
      this.setFilter(this.runFilter(filter), true);
    }
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

  // --------------React Table Setup -------------------------
  findAllValuesOfColumn = (columnFilter, valueAccessor) =>
    this.originalTools.map((tool, j) =>
      tool.columns.map((column, i) => {
        if (!columnFilter(tool, column)) {
          return undefined;
        }
        const values = this.originalTable
          .map((row) => valueAccessor(row.results[j], row.results[j].values[i]))
          .filter(Boolean);
        return [...new Set(values)].sort();
      }),
    );

  // -----------------------Common Functions-----------------------
  getRowName = (row) => row.id.filter((s) => s).join(" | ");

  changeTab = (_, column, tab) => {
    this.setState({
      tabIndex: tab,
      quantilePreSelection: column,
    });
  };

  render() {
    const reset = ({ className, isReset = false, onClick, enabled }) => (
      <FilterInfoButton
        className={className}
        showFilterText={isReset}
        onClick={onClick}
        enabled={enabled}
        isFiltered={!!this.state.filtered.length}
        resetFilters={this.resetFilters}
        filteredCount={this.state.table.length}
        totalCount={this.originalTable.length}
      />
    );
    let urlParams = document.location.href.split("?")[1] || "";
    urlParams = urlParams
      .split("&")
      .filter(
        (param) => param.startsWith("hidden") || param.startsWith("filter"),
      )
      .join("&");
    return (
      <Router ref={this.routerRef}>
        <div className="overview">
          <div className="overview-container">
            <FilterBox
              headerComponent={reset({
                className: "filterBox--header--reset",
                isReset: true,
                enabled: false,
              })}
              tableHeader={this.tableHeader}
              tools={this.state.tools}
              selectColumn={this.toggleSelectColumns}
              filterable={this.state.filterable}
              setFilter={this.filterPlotData}
              resetFilters={this.resetFilters}
              filtered={this.state.filtered}
              visible={this.state.filterBoxVisible}
              hiddenCols={this.state.hiddenCols}
              hide={() => {
                this.setState({ filterBoxVisible: false });
              }}
              ids={getTaskIdParts(this.originalTable, this.taskIdNames)}
            />
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
              {reset({
                className: "reset tooltip",
                enabled: true,
                onClick: () => {
                  this.setState({ filterBoxVisible: true });
                },
              })}
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
                    data={this.state.table}
                    tools={this.state.tools}
                    selectColumn={this.toggleSelectColumns}
                    setFilter={this.setFilter}
                    filterPlotData={this.filterPlotData}
                    filtered={this.state.filtered}
                    toggleLinkOverlay={this.toggleLinkOverlay}
                    changeTab={this.changeTab}
                    statusValues={this.statusValues}
                    categoryValues={this.categoryValues}
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
                    isFlexible={this.props.renderPlotsFlexible}
                  />
                </Route>
                <Route path="/scatter">
                  <ScatterPlot
                    table={this.state.table}
                    columns={this.columns}
                    tools={this.state.tools}
                    getRowName={this.getRowName}
                    hiddenCols={this.state.hiddenCols}
                    isFlexible={this.props.renderPlotsFlexible}
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
                history={this.routerRef.current.history}
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
