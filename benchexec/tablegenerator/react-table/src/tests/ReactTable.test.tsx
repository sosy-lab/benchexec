// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import React from "react";
import Table from "../components/ReactTable";
import { HashRouter as Router } from "react-router-dom";

import { test_snapshot_of } from "./utils";

type SnapshotSerializer = Parameters<typeof expect.addSnapshotSerializer>[0];

// Add a serializer that removes title attributes (irrelevant in our table)
expect.addSnapshotSerializer({
  print: (val, serialize) => {
    const v = val as { props?: { title?: unknown } };
    delete v.props?.title;
    return serialize(val);
  },
  test: (val) =>
    !!val &&
    typeof val === "object" &&
    "props" in (val as object) &&
    !!(val as { props?: unknown }).props &&
    Object.prototype.hasOwnProperty.call(
      (val as { props: Record<string, unknown> }).props,
      "title",
    ),
} as SnapshotSerializer);

test_snapshot_of("Render ReactTable", (overview) => {
  return (
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
  );
});
