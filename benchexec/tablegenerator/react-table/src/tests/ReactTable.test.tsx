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
expect.addSnapshotSerializer({
  print: (val: { props?: { title?: unknown } }, serialize: (v: unknown) => string) => {
    if (val.props) {
      delete val.props.title;
    }
    return serialize(val);
  },
  test: (val: unknown): val is { props: Record<string, unknown> } =>
    typeof val === "object" &&
    val !== null &&
    "props" in val &&
    typeof (val as { props?: unknown }).props === "object" &&
    (val as { props?: Record<string, unknown> }).props !== null &&
    Object.prototype.hasOwnProperty.call(
      (val as { props: Record<string, unknown> }).props,
      "title",
    ),
});

type SnapshotOverview = Parameters<typeof test_snapshot_of>[1] extends (
    overview: infer O,
  ) => unknown
  ? O
  : never;

test_snapshot_of("Render ReactTable", (overview: SnapshotOverview) => (
  <Router>
    <Table
      tableHeader={overview.tableHeader}
      tableData={overview.originalTable}
      tools={overview.tools}
      selectColumn={overview.toggleSelectColumns}
      prepareTableValues={overview.prepareTableValues}
      setFilter={overview.setFilter}
      filterPlotData={overview.filterPlotData}
      filters={overview.filteredData}
      toggleLinkOverlay={overview.toggleLinkOverlay}
      changeTab={overview.changeTab}
      statusValues={overview.statusValues}
      categoryValues={overview.categoryValues}
      hiddenCols={overview.hiddenCols}
    />
  </Router>
));