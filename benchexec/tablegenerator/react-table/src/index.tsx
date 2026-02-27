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

// `getElementById` can return null. We keep the runtime behavior
// (it should exist in production) but add a safe guard for type safety.
const rootEl = document.getElementById("root");
if (rootEl) {
  ReactDOM.render(<App />, rootEl);
}

// Remove loading message
// Guard against missing element to avoid runtime errors in non-standard environments (e.g. tests).
const msgContainerEl = document.getElementById("msg-container");
if (msgContainerEl) {
  msgContainerEl.remove();
}
