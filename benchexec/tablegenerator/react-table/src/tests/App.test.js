/* SPDX-License-Identifier: Apache-2.0
 *
 * BenchExec is a framework for reliable benchmarking.
 * This file is part of BenchExec.
 * Copyright (C) Dirk Beyer. All rights reserved.
 */
import App from "../App.js";
import React from "react";
import { test_snapshot_of } from "./utils.js";

// mock uniqid to have consistent names
// https://stackoverflow.com/a/44538270/396730
jest.mock("uniqid", () => i => i + "uniqid");

test_snapshot_of("Render App", overview => <App data={overview.data} />);
