// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import React from "react";
import Summary from "../components/Summary.js";

import { test_snapshot_of } from "./utils.js";

// mock uniqid to have consistent names
// https://stackoverflow.com/a/44538270/396730
jest.mock("uniqid", () => (i) => i + "uniqid");

test_snapshot_of("Render Summary", (overview) => (
  <Summary
    tools={overview.originalTools}
    tableHeader={overview.tableHeader}
    version={overview.props.data.version}
    selectColumn={overview.toggleSelectColumns}
    stats={overview.stats}
    prepareTableValues={overview.prepareTableValues}
    changeTab={overview.changeTab}
    hiddenCols={overview.state.hiddenCols}
  />
));
