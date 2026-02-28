// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import React from "react";
import Table from "../components/ReactTable.js";
import { HashRouter as Router } from "react-router-dom";

import { test_snapshot_of } from "./utils.js";

// Add a serializer that removes title attributes (irrelevant in our table)
type SnapshotSerializer = Parameters<typeof expect.addSnapshotSerializer>[0];

const hasTitleProp = (
  val: unknown,
): val is { props: Record<string, unknown> } =>
  typeof val === "object" &&
  val !== null &&
  "props" in val &&
  typeof (val as { props?: unknown }).props === "object" &&
  (val as { props?: Record<string, unknown> }).props !== null &&
  Object.prototype.hasOwnProperty.call(
    (val as { props: Record<string, unknown> }).props,
    "title",
  );

// Add a serializer that removes title attributes (irrelevant in our table)
const removeTitleSerializer: SnapshotSerializer = {
  test: hasTitleProp,
  print: (val, print) => {
    const v = val as { props?: { title?: unknown } };
    if (v.props) {
      delete v.props.title;
    }
    return print(val);
  },
};

expect.addSnapshotSerializer(removeTitleSerializer);

type TableProps = React.ComponentProps<typeof Table>;

type OverviewShape = {
  tableHeader: TableProps["tableHeader"];
  originalTable: TableProps["tableData"];
  tools: TableProps["tools"];
  toggleSelectColumns: TableProps["selectColumn"];
  prepareTableValues: TableProps["prepareTableValues"];
  setFilter: TableProps["setFilter"];
  filterPlotData: TableProps["filterPlotData"];
  filteredData: TableProps["filters"];
  toggleLinkOverlay: TableProps["toggleLinkOverlay"];
  changeTab: TableProps["changeTab"];
  statusValues: TableProps["statusValues"];
  categoryValues: TableProps["categoryValues"];
  hiddenCols: TableProps["hiddenCols"];
};

test_snapshot_of("Render ReactTable", (overview: unknown) => {
  const o = overview as unknown as OverviewShape;

  return (
    <Router>
      <Table
        tableHeader={o.tableHeader}
        tableData={o.originalTable}
        tools={o.tools}
        selectColumn={o.toggleSelectColumns}
        prepareTableValues={o.prepareTableValues}
        setFilter={o.setFilter}
        filterPlotData={o.filterPlotData}
        filters={o.filteredData}
        toggleLinkOverlay={o.toggleLinkOverlay}
        changeTab={o.changeTab}
        statusValues={o.statusValues}
        categoryValues={o.categoryValues}
        hiddenCols={o.hiddenCols}
      />
    </Router>
  );
});
