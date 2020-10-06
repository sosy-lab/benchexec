// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import React from "react";
import SelectColumn from "../components/SelectColumn.js";

import { test_snapshot_of } from "./utils.js";

test_snapshot_of("Render SelectColumn", (overview) => (
  <SelectColumn
    close={overview.toggleSelectColumns}
    tools={overview.state.tools}
    hiddenCols={overview.state.hiddenCols}
  />
));
