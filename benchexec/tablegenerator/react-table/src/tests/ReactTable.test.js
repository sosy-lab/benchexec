/* SPDX-License-Identifier: Apache-2.0
 *
 * BenchExec is a framework for reliable benchmarking.
 * This file is part of BenchExec.
 * Copyright (C) Dirk Beyer. All rights reserved.
 */
import React from "react";
import Table from "../components/ReactTable.js";

import { test_snapshot_of } from "./utils.js";

// mock uniqid to have consistent names
// https://stackoverflow.com/a/44538270/396730
jest.mock("uniqid", () => i => i + "uniqid");

// Add a serializer that removes title attributes (irrelevant in our table)
expect.addSnapshotSerializer({
  print: (val, serialize) => {
    delete val.props.title;
    return serialize(val);
  },
  test: val => val && val.props && val.props.hasOwnProperty("title")
});

test_snapshot_of("Render Summary", overview => (
  <Table
    tableHeader={overview.tableHeader}
    data={overview.originalTable}
    tools={overview.state.tools}
    properties={overview.properties}
    selectColumn={overview.toggleSelectColumns}
    getRunSets={overview.getRunSets}
    prepareTableValues={overview.prepareTableValues}
    setFilter={overview.setFilter}
    filterPlotData={overview.filterPlotData}
    filtered={overview.state.filtered}
    toggleLinkOverlay={overview.toggleLinkOverlay}
    changeTab={overview.changeTab}
  />
));
