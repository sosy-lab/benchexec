// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

// @ts-expect-error TS(6133): 'React' is declared but its value is never read.
import React from "react";
import SelectColumn from "../components/SelectColumn.js";

import { test_snapshot_of } from "./utils.js";

test_snapshot_of("Render SelectColumn", (overview: any) => (
  <SelectColumn
    // @ts-expect-error TS(2322): Type '{ close: any; tools: any; hiddenCols: any; }... Remove this comment to see the full error message
    close={overview.toggleSelectColumns}
    tools={overview.tools}
    hiddenCols={overview.hiddenCols}
  />
));
