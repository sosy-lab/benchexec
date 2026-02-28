// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import React from "react";
import SelectColumn from "../components/SelectColumn";

import { test_snapshot_of } from "./utils";

type SelectColumnProps = React.ComponentProps<typeof SelectColumn>;

type OverviewShape = {
  toggleSelectColumns: SelectColumnProps["close"];
  tools: SelectColumnProps["tools"];
  hiddenCols: SelectColumnProps["hiddenCols"];
};

test_snapshot_of("Render SelectColumn", (overview: unknown) => {
  const o = overview as unknown as OverviewShape;

  return (
    <SelectColumn
      close={o.toggleSelectColumns}
      tools={o.tools}
      hiddenCols={o.hiddenCols}
      updateParentStateOnClose={() => undefined}
    />
  );
});
