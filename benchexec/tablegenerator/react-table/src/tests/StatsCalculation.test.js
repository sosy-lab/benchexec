// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import React from "react";
import Summary from "../components/Summary.js";
import fs from "fs";
import renderer from "react-test-renderer";
import { getOverviewProps } from "./utils.js";
import { computeStats, filterComputableStatistics } from "../utils/stats.js";
const testDir = "../test_integration/expected/";

fs.readdirSync(testDir)
  .filter((file) => file.endsWith(".html"))
  .forEach((file) => {
    describe("StatisticsTable for " + file, () => {
      let content;
      let data;
      let overviewProps;
      let jsStatComponent;
      let pythonStatComponent;

      beforeAll(async () => {
        content = fs.readFileSync(testDir + file, { encoding: "UTF-8" });
        data = JSON.parse(content);
        overviewProps = getOverviewProps(data);
        await renderer.act(async () => {
          pythonStatComponent = renderer.create(
            <Summary
              tools={overviewProps.originalTools}
              tableHeader={overviewProps.tableHeader}
              version={overviewProps.data.version}
              selectColumn={overviewProps.toggleSelectColumns}
              tableData={overviewProps.tableData}
              prepareTableValues={overviewProps.prepareTableValues}
              changeTab={overviewProps.changeTab}
              onStatsReady={overviewProps.onStatsReady}
              hiddenCols={overviewProps.hiddenCols}
              stats={filterComputableStatistics(overviewProps.stats)}
            />,
          );
        });

        const jsStats = await computeStats(overviewProps);
        await renderer.act(async () => {
          jsStatComponent = renderer.create(
            <Summary
              tools={overviewProps.originalTools}
              tableHeader={overviewProps.tableHeader}
              version={overviewProps.data.version}
              selectColumn={overviewProps.toggleSelectColumns}
              tableData={overviewProps.tableData}
              prepareTableValues={overviewProps.prepareTableValues}
              changeTab={overviewProps.changeTab}
              onStatsReady={overviewProps.onStatsReady}
              hiddenCols={overviewProps.hiddenCols}
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
