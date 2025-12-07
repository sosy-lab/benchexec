// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import React from "react";
import ReactDOM from "react-dom";
import { act } from "react-dom/test-utils";
import App from "./App";

it("renders without crashing", async () => {
  const div = document.createElement("div");
  let statsResolver;
  const StatsReadyPromise = new Promise((resolve) => (statsResolver = resolve));
  await act(async () => {
    ReactDOM.render(<App onStatsReady={statsResolver} />, div);
    await StatsReadyPromise;
  });
  ReactDOM.unmountComponentAtNode(div);
});
