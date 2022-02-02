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
import { buildFormatter, processData, cleanupStats } from "../utils/stats.js";
import { isNotNil } from "../utils/utils";
const testDir = "../test_integration/expected/";

const subStatSelector = {
  "total results": "total",
  "correct results": "correct-total",
  "correct true": "correct-true",
  "correct false": "correct-false",
  "incorrect results": "wrong-total",
  "incorrect true": "wrong-true",
  "incorrect false": "wrong-false",
};

const transformWorkerStats = async (overviewProps) => {
  const formatter = buildFormatter(overviewProps.tools);
  let jsStats = await processData({
    tools: overviewProps.tools,
    tableData: overviewProps.tableData,
    formatter,
    stats: overviewProps.stats,
  });

  const availableStats = overviewProps.stats
    .map((row) => subStatSelector[row.title.replace(/&nbsp;/g, "")])
    .filter(isNotNil);

  const cleaned = cleanupStats(jsStats, formatter, availableStats);

  jsStats = cleaned.map((tool, toolIdx) => {
    const out = [];
    const toolColumns = overviewProps.tools[toolIdx].columns;
    let pointer = 0;
    let curr = toolColumns[pointer];
    for (const col of tool) {
      const { title } = col;
      while (pointer < toolColumns.length && title !== curr.title) {
        // irrelevant column
        out.push({});
        pointer++;
        curr = toolColumns[pointer];
      }
      if (pointer >= toolColumns.length) {
        break;
      }
      // relevant column
      out.push(col);
      pointer++;
      curr = toolColumns[pointer];
    }
    return out;
  });

  const transformed = overviewProps.stats.map((row) => {
    const title = row.title.replace(/&nbsp;/g, "");
    row.content = row.content.map((tool, toolIdx) => {
      const key = subStatSelector[title];
      if (!key || !jsStats[toolIdx]) {
        return tool;
      }
      return jsStats[toolIdx].map((col) => col[key]);
    });
    return row;
  });

  return transformed;
};

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
              stats={overviewProps.stats}
              filtered={overviewProps.filteredData.length > 0}
            />,
          );
        });

        const jsStats = await transformWorkerStats(overviewProps);
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
