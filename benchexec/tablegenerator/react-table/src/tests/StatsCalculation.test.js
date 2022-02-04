// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import React from "react";
import StatisticsTable from "../components/StatisticsTable.js";
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
            <StatisticsTable
              selectColumn={overviewProps.toggleSelectColumns}
              tools={overviewProps.tools}
              switchToQuantile={overviewProps.switchToQuantile}
              hiddenCols={overviewProps.hiddenCols}
              tableData={overviewProps.tableData}
              stats={filterComputableStatistics(overviewProps.stats)}
              filtered={overviewProps.filteredData.length > 0}
            />,
          );
        });

        const jsStats = filterComputableStatistics(
          await computeStats({
            ...overviewProps,
            asFiltered: false,
          }),
        );
        await renderer.act(async () => {
          jsStatComponent = renderer.create(
            <StatisticsTable
              selectColumn={overviewProps.toggleSelectColumns}
              tools={overviewProps.tools}
              switchToQuantile={overviewProps.switchToQuantile}
              hiddenCols={overviewProps.hiddenCols}
              tableData={overviewProps.tableData}
              stats={jsStats}
              filtered={overviewProps.filteredData.length > 0}
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
