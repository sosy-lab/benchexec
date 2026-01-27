// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import React from "react";
import App from "./App";
import { render } from "@testing-library/react";

it("renders without crashing", async () => {
  let statsResolver;
  const StatsReadyPromise = new Promise((resolve) => (statsResolver = resolve));

  const { unmount } = render(<App onStatsReady={statsResolver} />);

  await StatsReadyPromise;
  unmount();
});
