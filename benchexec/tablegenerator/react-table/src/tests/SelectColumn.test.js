/* SPDX-License-Identifier: Apache-2.0
 *
 * BenchExec is a framework for reliable benchmarking.
 * This file is part of BenchExec.
 * Copyright (C) Dirk Beyer. All rights reserved.
 */
import React from "react";
import ReactModal from "react-modal";
import SelectColumn from "../components/SelectColumn.js";

import { test_snapshot_of } from "./utils.js";

// mock uniqid to have consistent names
// https://stackoverflow.com/a/44538270/396730
jest.mock("uniqid", () => i => i + "uniqid");

ReactModal.setAppElement(document.createElement("div"));

test_snapshot_of("Render SelectColumn", overview => (
  <SelectColumn
    close={overview.toggleSelectColumns}
    tools={overview.state.tools}
  />
));
