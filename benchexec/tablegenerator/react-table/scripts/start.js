/* SPDX-License-Identifier: Apache-2.0
 *
 * BenchExec is a framework for reliable benchmarking.
 * This file is part of BenchExec.
 * Copyright (C) Dirk Beyer. All rights reserved.
 */
"use strict";

const fs = require("fs");
const path = require("path");

const dataParam = process.argv[2];

if (dataParam) {
  // the path in this variable will be bound to @data
  process.env.DATA = "src/data/custom-data.json";

  fs.copyFileSync(
    path.resolve(__dirname, "../", dataParam),
    path.resolve(process.env.DATA)
  );
}

require("react-app-rewired/scripts/start");
