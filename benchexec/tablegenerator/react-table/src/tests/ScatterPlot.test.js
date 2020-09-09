// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import React from "react";
import ScatterPlot from "../components/ScatterPlot.js";
import Overview from "../components/Overview";
import renderer from "react-test-renderer";
import { setParam } from "../utils/utils";
import { getPlotOptions } from "./utils.js";
const fs = require("fs");

const testDir = "../test_integration/expected/";

fs.readdirSync(testDir)
  .filter((file) => file.endsWith(".html"))
  .filter((file) => fs.statSync(testDir + file).size < 100000)
  .forEach((file) => {
    describe("Scatter Plot tests for " + file, () => {
      const content = fs.readFileSync(testDir + file, { encoding: "UTF-8" });
      const data = JSON.parse(content);
      const overview = renderer.create(<Overview data={data} />).getInstance();
      const scatterPlotJSX = (
        <ScatterPlot
          table={overview.state.table}
          tools={overview.state.tools}
          columns={overview.columns}
          getRowName={overview.getRowName}
          hiddenCols={overview.state.hiddenCols}
          isFlexible={false}
          fixedWidth={1500}
          fixedHeight={1000}
        />
      );
      const plot = renderer.create(scatterPlotJSX);
      const plotInstance = plot.getInstance();

      // Store a reference of the tool the column belongs to in the column for later use
      const colsWithToolReference = plotInstance.props.tools.flatMap((tool) =>
        tool.columns.map((col) => ({ ...col, toolIdx: tool.toolIdx })),
      );

      /* Objects of all first occuring columns with an unique type attribute of the format {runsetIdx}-{colIdx} and
         its corresponding type. Overriding of toString() method is used for better identifying test cases. */
      const selectionOptions = colsWithToolReference
        .filter(
          (col, index, self) =>
            self.map((col2) => col2.type).indexOf(col.type) === index,
        )
        .map((col) => ({
          value: col.toolIdx + "-" + col.colIdx,
          type: col.type,
          toString: () => col.type,
        }));
      const resultOptions = getPlotOptions(plot, "Results");

      /* Array of triples of the selection for the x-axis, y-axis and shown results that will be chosen for a test
         of the plot. Contains all combinations of the first columns of different types with all result options. */
      const selectionResultInput = selectionOptions.flatMap((xAxis, i) =>
        selectionOptions
          .slice(i)
          .flatMap((yAxis) =>
            resultOptions.map((result) => [xAxis, yAxis, result]),
          ),
      );

      describe("Scatter Plot should match HTML snapshot", () => {
        it.each(selectionResultInput)(
          "with X-Axis of the type %s and Y-Axis of the type %s and %s results",
          (xSelection, ySelection, results) => {
            let [toolX, columnX] = xSelection.value.split("-");
            let [toolY, columnY] = ySelection.value.split("-");
            columnX = columnX.replace("___", "-");
            columnY = columnY.replace("___", "-");

            setParam({ toolX, columnX, toolY, columnY });
            plotInstance.refreshUrlState();
            expect(plot).toMatchSnapshot();
          },
        );
      });
    });
  });
