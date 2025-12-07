// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import React from "react";
import { HashRouter as Router, Routes, Route, Link } from "react-router-dom";
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
  statusForEmptyRows,
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

require("setimmediate"); // provides setImmediate and clearImmediate

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
  categoryValues: any;
  columns: any;
  filterUrlRetriever: any;
  filterUrlSetter: any;
  filteredData: any;
  lastFiltered: any;
  lastImmediate: any;
  originalTable: any;
  originalTools: any;
  stats: any;
  statusValues: any;
  tableHeader: any;
  taskIdNames: any;
  constructor(props: any) {
    super(props);

    // imported data
    const {
      tableHeader,
      taskIdNames,
      tools,
      columns,
      tableData,
      stats,
      initial,
    } = prepareTableData(props.data);

    if (initial && !document.location.href.includes("#")) {
      setConstantHashSearch(initial);
    }

    // @ts-expect-error TS(2339): Property 'data' does not exist on type 'Readonly<{... Remove this comment to see the full error message
    const filterable = getFilterableData(this.props.data);
    this.originalTable = tableData;
    this.originalTools = tools;

    this.taskIdNames = taskIdNames;

    this.columns = columns;
    this.stats = stats;
    this.tableHeader = tableHeader;

    this.filteredData = [];

    // data is handled and changed here; To use it in other components hand it over with component
    // To change data in component (e.g. filter): function to change has to be in overview
    this.state = {
      tools,
      tableData,
      filterable,
      showSelectColumns: false,
      showLinkOverlay: false,
      filtered: [],
      filterBoxVisible: false,
      active: getActiveTab(),
      quantilePreSelection: tools[0].columns[1],
      hiddenCols: createHiddenColsFromURL(tools),
    };
    // Collect all status and category values for filter drop-down
    this.statusValues = this.findAllValuesOfColumn(
      (_tool: any, column: any) => column.type === "status",
      // @ts-expect-error TS(2554): Expected 2 arguments, but got 1.
      (_runResult: any, value: any) => getRawOrDefault(value),
    );
    // Add statusForEmptyRows to status values array if there is a corresponding empty row for the runset
    this.originalTools.forEach((tool: any, j: any) =>
      tool.columns
        .filter((column: any) => column.type === "status")
        // @ts-expect-error TS(6133): 'col' is declared but its value is never read.
        .forEach((col: any, i: any) => {
          const hasEmptyRow = this.originalTable.some(
            (row: any) => row.results[j].category === "empty",
          );
          if (hasEmptyRow) {
            this.statusValues[j][i].push(statusForEmptyRows);
          }
        }),
    );
    this.categoryValues = this.findAllValuesOfColumn(
      (_tool: any, column: any) => column.type === "status",
      (runResult: any, _value: any) => runResult.category,
    );

    const categoryValuesWithTrailingSpace = this.categoryValues.map(
      (tool: any) =>
        tool &&
        tool.map(
          (column: any) => column && column.map((item: any) => `${item} `),
        ),
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
        tableData: this.filteredData,
        filtered: deserializedFilters,
      };
    }
  }

  addTypeToFilter = (filters: any) => {
    return filters
      .filter((filter: any) => filter.id !== "id")
      .forEach((filter: any) => {
        const filterSplitArray = filter.id.split("_");
        const type =
          // @ts-expect-error TS(2339): Property 'tools' does not exist on type 'Readonly<... Remove this comment to see the full error message
          this.state.tools[filterSplitArray[0]]["columns"][
            filterSplitArray.at(-1)
          ].type;
        filter.type = type;
      });
  };

  componentDidMount() {
    this.updateFiltersFromUrl();
    this.updateState();
  }

  getFiltersFromUrl = () => {
    const deserializedFilters = this.filterUrlRetriever() || [];
    this.addTypeToFilter(deserializedFilters);
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
        tableData: this.filteredData,
        filtered: newFilters,
      });
      this.lastFiltered = newFilters;
    }
  };

  updateState = () =>
    this.setState({
      active: getActiveTab(),
      // @ts-expect-error TS(2339): Property 'tools' does not exist on type 'Readonly<... Remove this comment to see the full error message
      hiddenCols: createHiddenColsFromURL(this.state.tools),
    });

  // -----------------------SelectColumns-----------------------
  toggleSelectColumns = (ev: any) => {
    ev.stopPropagation();

    this.setState((prevState) => ({
      // @ts-expect-error TS(2339): Property 'showSelectColumns' does not exist on typ... Remove this comment to see the full error message
      showSelectColumns: !prevState.showSelectColumns,
    }));
  };

  // -----------------------Link Overlay-----------------------
  toggleLinkOverlay = (ev: any, hrefRow: any) => {
    ev.preventDefault();

    this.setState((prevState) => ({
      // @ts-expect-error TS(2339): Property 'showLinkOverlay' does not exist on type ... Remove this comment to see the full error message
      showLinkOverlay: !prevState.showLinkOverlay,
      link: hrefRow,
    }));
  };

  // -----------------------Filter-----------------------
  setFilter = (filteredData: any, raw = false) => {
    if (raw) {
      this.filteredData = filteredData;
      return;
    }
    this.filteredData = filteredData.map((row: any) => {
      return row._original;
    });
  };

  runFilter(filter: any) {
    const matcher = buildMatcher(filter);
    return applyMatcher(matcher)(this.originalTable);
  }

  filterPlotData = (filter: any, runFilterLogic = true) => {
    // updating url filters on next tick to ensure that state is already set
    // when handler is called);
    if (this.lastImmediate) {
      clearImmediate(this.lastImmediate);
    }
    this.lastImmediate = setImmediate(() => {
      this.filterUrlSetter(filter, {
        pushState: true,
        callbacks: [this.updateFiltersFromUrl, this.updateState],
      });
      this.lastFiltered = filter.filter(
        (item: any) => (item.values && item.values.length > 0) || item.value,
      );
    });
    if (runFilterLogic) {
      this.setFilter(this.runFilter(filter), true);
    }
    this.setState({
      tableData: this.filteredData,
      filtered: filter,
    });
  };

  resetFilters = () => {
    this.setState({
      tableData: this.originalTable,
      filtered: [],
    });
  };

  // --------------React Table Setup -------------------------
  findAllValuesOfColumn = (columnFilter: any, valueAccessor: any) =>
    this.originalTools.map((tool: any, j: any) =>
      tool.columns.map((column: any, i: any) => {
        if (!columnFilter(tool, column)) {
          return undefined;
        }
        const values = this.originalTable
          .map((row: any) =>
            valueAccessor(row.results[j], row.results[j].values[i]),
          )
          .filter(Boolean);
        return [...new Set(values)].sort();
      }),
    );

  // -----------------------Common Functions-----------------------
  getRowName = (row: any) => row.id.filter((s: any) => s).join(" | ");

  // Return URL params that are important across different tabs, i.e. hidden cols and filter. Returns an empty string if there are none.
  getRelevantUrlParams = () => {
    let urlParams = document.location.href.split("?")[1] || "";
    return urlParams
      .split("&")
      .filter(
        (param) => param.startsWith("hidden") || param.startsWith("filter"),
      )
      .join("&");
  };

  // Open the quantile Plot with the given preselection
  switchToQuantile = (quantilePreSelection: any) => {
    this.setState({ quantilePreSelection });
    const urlParams = this.getRelevantUrlParams();
    document.location.hash = "#/quantile" + (urlParams ? "?" + urlParams : "");
  };

  render() {
    const reset = ({ className, isReset = false, onClick, enabled }: any) => (
      <FilterInfoButton
        // @ts-expect-error TS(2769): No overload matches this call.
        className={className}
        showFilterText={isReset}
        onClick={onClick}
        enabled={enabled}
        // @ts-expect-error TS(2339): Property 'filtered' does not exist on type 'Readon... Remove this comment to see the full error message
        isFiltered={!!this.state.filtered.length}
        resetFilters={this.resetFilters}
        // @ts-expect-error TS(2339): Property 'tableData' does not exist on type 'Reado... Remove this comment to see the full error message
        filteredCount={this.state.tableData.length}
        totalCount={this.originalTable.length}
      />
    );

    const urlParams = this.getRelevantUrlParams();

    return (
      <Router>
        <div className="overview">
          <div className="overview-container">
            <FilterBox
              // @ts-expect-error TS(2322): Type '{ headerComponent: Element; tableHeader: any... Remove this comment to see the full error message
              headerComponent={reset({
                className: "filterBox--header--reset",
                isReset: true,
                enabled: false,
              })}
              tableHeader={this.tableHeader}
              // @ts-expect-error TS(2339): Property 'tools' does not exist on type 'Readonly<... Remove this comment to see the full error message
              tools={this.state.tools}
              selectColumn={this.toggleSelectColumns}
              // @ts-expect-error TS(2339): Property 'filterable' does not exist on type 'Read... Remove this comment to see the full error message
              filterable={this.state.filterable}
              setFilter={this.filterPlotData}
              resetFilters={this.resetFilters}
              // @ts-expect-error TS(2339): Property 'filtered' does not exist on type 'Readon... Remove this comment to see the full error message
              filtered={this.state.filtered}
              // @ts-expect-error TS(2339): Property 'filterBoxVisible' does not exist on type... Remove this comment to see the full error message
              visible={this.state.filterBoxVisible}
              // @ts-expect-error TS(2339): Property 'hiddenCols' does not exist on type 'Read... Remove this comment to see the full error message
              hiddenCols={this.state.hiddenCols}
              hide={() => {
                this.setState({ filterBoxVisible: false });
              }}
              ids={getTaskIdParts(this.originalTable, this.taskIdNames)}
              addTypeToFilter={this.addTypeToFilter}
            />
            <div className="menu">
              {menuItems.map(({ key, title, path, icon }) => (
                <Link
                  className={classNames("menu-item", {
                    // @ts-expect-error TS(2339): Property 'active' does not exist on type 'Readonly... Remove this comment to see the full error message
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
              <Routes>
                <Route
                  path="/"
                  element={
                    <Summary
                      // @ts-expect-error TS(2339): Property 'tools' does not exist on type 'Readonly<... Remove this comment to see the full error message
                      tools={this.state.tools}
                      tableHeader={this.tableHeader}
                      // @ts-expect-error TS(2339): Property 'data' does not exist on type 'Readonly<{... Remove this comment to see the full error message
                      version={this.props.data.version}
                      selectColumn={this.toggleSelectColumns}
                      stats={this.stats}
                      // @ts-expect-error TS(2339): Property 'onStatsReady' does not exist on type 'Re... Remove this comment to see the full error message
                      onStatsReady={this.props.onStatsReady}
                      switchToQuantile={this.switchToQuantile}
                      // @ts-expect-error TS(2339): Property 'tableData' does not exist on type 'Reado... Remove this comment to see the full error message
                      tableData={this.state.tableData}
                      // @ts-expect-error TS(2339): Property 'hiddenCols' does not exist on type 'Read... Remove this comment to see the full error message
                      hiddenCols={this.state.hiddenCols}
                      // @ts-expect-error TS(2339): Property 'filtered' does not exist on type 'Readon... Remove this comment to see the full error message
                      filtered={this.state.filtered.length > 0}
                    />
                  }
                />
                <Route
                  path="/table"
                  element={
                    <Table
                      // @ts-expect-error TS(2339): Property 'tableData' does not exist on type 'Reado... Remove this comment to see the full error message
                      tableData={this.state.tableData}
                      // @ts-expect-error TS(2339): Property 'tools' does not exist on type 'Readonly<... Remove this comment to see the full error message
                      tools={this.state.tools}
                      selectColumn={this.toggleSelectColumns}
                      filterPlotData={this.filterPlotData}
                      // @ts-expect-error TS(2339): Property 'filtered' does not exist on type 'Readon... Remove this comment to see the full error message
                      filters={this.state.filtered}
                      toggleLinkOverlay={this.toggleLinkOverlay}
                      statusValues={this.statusValues}
                      categoryValues={this.categoryValues}
                      // @ts-expect-error TS(2339): Property 'hiddenCols' does not exist on type 'Read... Remove this comment to see the full error message
                      hiddenCols={this.state.hiddenCols}
                      addTypeToFilter={this.addTypeToFilter}
                    />
                  }
                />
                <Route
                  path="/quantile"
                  element={
                    <QuantilePlot
                      // @ts-expect-error TS(2322): Type '{ table: any; tools: any; preSelection: any;... Remove this comment to see the full error message
                      table={this.state.tableData}
                      // @ts-expect-error TS(2339): Property 'tools' does not exist on type 'Readonly<... Remove this comment to see the full error message
                      tools={this.state.tools}
                      // @ts-expect-error TS(2339): Property 'quantilePreSelection' does not exist on ... Remove this comment to see the full error message
                      preSelection={this.state.quantilePreSelection}
                      getRowName={this.getRowName}
                      // @ts-expect-error TS(2339): Property 'hiddenCols' does not exist on type 'Read... Remove this comment to see the full error message
                      hiddenCols={this.state.hiddenCols}
                      // @ts-expect-error TS(2339): Property 'renderPlotsFlexible' does not exist on t... Remove this comment to see the full error message
                      isFlexible={this.props.renderPlotsFlexible}
                    />
                  }
                />
                <Route
                  path="/scatter"
                  element={
                    <ScatterPlot
                      // @ts-expect-error TS(2322): Type '{ table: any; columns: any; tools: any; getR... Remove this comment to see the full error message
                      table={this.state.tableData}
                      columns={this.columns}
                      // @ts-expect-error TS(2339): Property 'tools' does not exist on type 'Readonly<... Remove this comment to see the full error message
                      tools={this.state.tools}
                      getRowName={this.getRowName}
                      // @ts-expect-error TS(2339): Property 'hiddenCols' does not exist on type 'Read... Remove this comment to see the full error message
                      hiddenCols={this.state.hiddenCols}
                      // @ts-expect-error TS(2339): Property 'renderPlotsFlexible' does not exist on t... Remove this comment to see the full error message
                      isFlexible={this.props.renderPlotsFlexible}
                    />
                  }
                />
                <Route
                  path="/info"
                  element={
                    <Info
                      // @ts-expect-error TS(2339): Property 'data' does not exist on type 'Readonly<{... Remove this comment to see the full error message
                      version={this.props.data.version}
                      selectColumn={this.toggleSelectColumns}
                    />
                  }
                />
              </Routes>
            </div>
          </div>
          <div>
            // @ts-expect-error TS(2339): Property 'showSelectColumns' does not
            exist on typ... Remove this comment to see the full error message
            {this.state.showSelectColumns && (
              <SelectColumn
                // @ts-expect-error TS(2322): Type '{ close: (ev: any) => void; currColumns: any... Remove this comment to see the full error message
                close={this.toggleSelectColumns}
                currColumns={this.columns}
                tableHeader={this.tableHeader}
                // @ts-expect-error TS(2339): Property 'tools' does not exist on type 'Readonly<... Remove this comment to see the full error message
                tools={this.state.tools}
                // @ts-expect-error TS(2339): Property 'hiddenCols' does not exist on type 'Read... Remove this comment to see the full error message
                hiddenCols={this.state.hiddenCols}
                updateParentStateOnClose={() => {
                  this.updateState();
                  this.updateFiltersFromUrl();
                }}
              />
            )}
            // @ts-expect-error TS(2339): Property 'showLinkOverlay' does not
            exist on type ... Remove this comment to see the full error message
            {this.state.showLinkOverlay && (
              <LinkOverlay
                // @ts-expect-error TS(2322): Type '{ close: (ev: any, hrefRow: any) => void; li... Remove this comment to see the full error message
                close={this.toggleLinkOverlay}
                // @ts-expect-error TS(2339): Property 'link' does not exist on type 'Readonly<{... Remove this comment to see the full error message
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
