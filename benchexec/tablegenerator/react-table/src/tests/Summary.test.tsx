// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import React from "react";
import Summary from "../components/Summary";

import { test_snapshot_of_async } from "./utils";

type SummaryProps = React.ComponentProps<typeof Summary>;
type StatsReadyResolver = SummaryProps["onStatsReady"];

test_snapshot_of_async("Render Summary", (overview) => {
  let statsResolver!: StatsReadyResolver;
  const StatsReadyPromise = new Promise<void>((resolve) => {
    statsResolver = resolve;
  });

  const out = (
    <Summary
      {...({
        tools: overview.originalTools,
        tableHeader: overview.tableHeader,
        version: overview.data.version,
        selectColumn: overview.toggleSelectColumns,
        stats: overview.stats,
        tableData: overview.tableData,
        prepareTableValues: overview.prepareTableValues,
        changeTab: overview.changeTab,
        onStatsReady: statsResolver,
        hiddenCols: overview.hiddenCols,
      } as Partial<SummaryProps> as SummaryProps)}
    />
  );

  return { component: out, promise: StatsReadyPromise };
});
