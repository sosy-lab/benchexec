// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import React from "react";
import StatisticsTable from "../components/StatisticsTable";
import fs from "fs";
import * as renderer from "react-test-renderer";
import { getOverviewProps } from "./utils";
import { computeStats, filterComputableStatistics } from "../utils/stats";

const testDir = "../test_integration/expected/";

/* ============================================================
 * Types
 * ============================================================ */

type StatisticsTableProps = React.ComponentProps<typeof StatisticsTable>;
type StatsComponent = renderer.ReactTestRenderer;

type OverviewProps = ReturnType<typeof getOverviewProps>;

fs.readdirSync(testDir)
  .filter((file) => file.endsWith(".html"))
  .forEach((file) => {
    describe("StatisticsTable for " + file, () => {
      let content: string;
      let data: unknown;
      let overviewProps: OverviewProps;
      let jsStatComponent: StatsComponent;
      let pythonStatComponent: StatsComponent;

      beforeAll(async () => {
        content = fs.readFileSync(testDir + file, { encoding: "utf-8" });
        data = JSON.parse(content) as unknown;

        overviewProps = getOverviewProps(data);

        await renderer.act(async () => {
          pythonStatComponent = renderer.create(
            <StatisticsTable
              selectColumn={overviewProps.toggleSelectColumns}
              tools={overviewProps.tools}
              switchToQuantile={overviewProps.switchToQuantile}
              hiddenCols={overviewProps.hiddenCols}
              tableData={
                overviewProps.tableData as unknown as StatisticsTableProps["tableData"]
              }
              stats={
                filterComputableStatistics(
                  overviewProps.stats,
                ) as unknown as StatisticsTableProps["stats"]
              }
            />,
          );
        });

        const jsStats = (await computeStats(
          overviewProps as unknown as Parameters<typeof computeStats>[0],
        )) as unknown as StatisticsTableProps["stats"];

        await renderer.act(async () => {
          jsStatComponent = renderer.create(
            <StatisticsTable
              selectColumn={overviewProps.toggleSelectColumns}
              tools={overviewProps.tools}
              switchToQuantile={overviewProps.switchToQuantile}
              hiddenCols={overviewProps.hiddenCols}
              tableData={
                overviewProps.tableData as unknown as StatisticsTableProps["tableData"]
              }
              stats={jsStats}
            />,
          );
        });
      });

      it("Compare StatisticsTable using python-computed stats", () => {
        expect(pythonStatComponent).toMatchSnapshot();
      });

      it("Compare StatisticsTable using js-computed stats", () => {
        expect(jsStatComponent).toMatchSnapshot();
      });

      it("StatisticsTable stats computed using python and js should be identical", () => {
        expect(JSON.stringify(jsStatComponent.toJSON(), null, 1)).toEqual(
          JSON.stringify(pythonStatComponent.toJSON(), null, 1),
        );
      });
    });
  });
