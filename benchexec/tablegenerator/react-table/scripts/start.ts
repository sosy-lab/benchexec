// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

// @ts-expect-error TS(2451): Cannot redeclare block-scoped variable 'fs'.
const fs = require("fs");
// @ts-expect-error TS(2451): Cannot redeclare block-scoped variable 'path'.
const path = require("path");

const dataParam = process.argv[2];

if (dataParam) {
  // the path in this variable will be bound to @data
  process.env.DATA = "src/data/custom-data.json";

  fs.copyFileSync(
    path.resolve(__dirname, "../", dataParam),
    path.resolve(process.env.DATA),
  );
}

require("react-app-rewired/scripts/start");
