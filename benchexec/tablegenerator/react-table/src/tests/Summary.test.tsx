// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import React from "react";
import Summary from "../components/Summary";

import { test_snapshot_of_async } from "./utils.js";

type SummaryProps = React.ComponentProps<typeof Summary>;
type StatsReadyResolver = SummaryProps["onStatsReady"];

type OverviewForSummary = {
  originalTools: unknown;
  tableHeader: unknown;
  data: { version: unknown };
  toggleSelectColumns: unknown;
  stats: unknown;
  tableData: unknown;
  prepareTableValues: unknown;
  changeTab: unknown;
  hiddenCols: unknown;
};

test_snapshot_of_async("Render Summary", (overview: unknown) => {
  const o = overview as OverviewForSummary;

  let statsResolver!: StatsReadyResolver;
  const StatsReadyPromise = new Promise<void>((resolve) => {
    statsResolver = resolve;
  });

  const out = (
    <Summary
      {...({
        tools: o.originalTools,
        tableHeader: o.tableHeader,
        version: o.data.version,
        selectColumn: o.toggleSelectColumns,
        stats: o.stats,
        tableData: o.tableData,
        prepareTableValues: o.prepareTableValues,
        changeTab: o.changeTab,
        onStatsReady: statsResolver,
        hiddenCols: o.hiddenCols,
      } as Partial<SummaryProps> as SummaryProps)}
    />
  );

  return { component: out, promise: StatsReadyPromise };
});
