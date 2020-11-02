// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import React from "react";
import ReactDOM from "react-dom";
import "./index.css";
import App from "./App";

// Remove loading message
document.getElementById("msg-container").remove();
ReactDOM.render(<App />, document.getElementById("root"));
