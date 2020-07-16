// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import React from "react";
import Table from "../components/ReactTable.js";

import { test_snapshot_of } from "./utils.js";

// Add a serializer that removes title attributes (irrelevant in our table)
expect.addSnapshotSerializer({
  print: (val, serialize) => {
    delete val.props.title;
    return serialize(val);
  },
  test: (val) => val && val.props && val.props.hasOwnProperty("title"),
});

test_snapshot_of("Render Summary", (overview) => (
  <Table
    tableHeader={overview.tableHeader}
    data={overview.originalTable}
    tools={overview.state.tools}
    selectColumn={overview.toggleSelectColumns}
    prepareTableValues={overview.prepareTableValues}
    setFilter={overview.setFilter}
    filterPlotData={overview.filterPlotData}
    filtered={overview.state.filtered}
    toggleLinkOverlay={overview.toggleLinkOverlay}
    changeTab={overview.changeTab}
    statusValues={overview.statusValues}
    categoryValues={overview.categoryValues}
    hiddenCols={overview.state.hiddenCols}
  />
));
