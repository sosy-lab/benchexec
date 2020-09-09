// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import React from "react";
import QuantilePlot from "../components/QuantilePlot.js";
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
    describe("Quantile Plot tests for " + file, () => {
      const content = fs.readFileSync(testDir + file, { encoding: "UTF-8" });
      const data = JSON.parse(content);
      const overview = renderer.create(<Overview data={data} />).getInstance();
      const quantilePlotJSX = (
        <QuantilePlot
          table={overview.state.table}
          tools={overview.state.tools}
          preSelection={overview.state.quantilePreSelection}
          getRowName={overview.getRowName}
          hiddenCols={overview.state.hiddenCols}
          isFlexible={false}
          fixedWidth={1500}
          fixedHeight={1000}
        />
      );
      const plot = renderer.create(quantilePlotJSX);
      const plotInstance = plot.getInstance();

      /* Objects of all first occuring columns with an unique type attribute as well as all runsets and their
         corresponding types. Overriding of toString() method is used for better identifying test cases. */
      const selectionOptions = plotInstance.possibleValues
        .filter(
          (col, index, self) =>
            self.map((col2) => col2.type).indexOf(col.type) === index,
        )
        .map((col) => ({
          value: col.display_title,
          type: col.type,
          toString: () => col.type,
        }))
        .concat(
          plotInstance.props.tools.map((tool) => ({
            value: "runset-" + tool.toolIdx,
            type: "runset",
            toString: () => "runset",
          })),
        );
      const resultOptions = getPlotOptions(plot, "Results");

      // Array of pairs of selection and shown results that will be chosen for a test of the plot
      const selectionResultInput = selectionOptions.flatMap((selection) =>
        resultOptions.map((result) => [selection, result]),
      );

      describe("Quantile Plot should match HTML snapshot", () => {
        setParam({ plot: plotInstance.plotOptions.quantile });

        it.each(selectionResultInput)(
          "with selection of the type %s and %s results",
          (selection, results) => {
            setParam({ selection: selection.value, results });
            plotInstance.refreshUrlState();
            expect(plot).toMatchSnapshot();
          },
        );
      });

      describe("Direct Plot should match HTML snapshot", () => {
        setParam({ plot: plotInstance.plotOptions.direct });

        it.each(selectionResultInput)(
          "with selection of the type %s and %s results",
          (selection, results) => {
            setParam({ selection: selection.value, results });
            plotInstance.refreshUrlState();
            expect(plot).toMatchSnapshot();
          },
        );
      });

      describe("Score-based Quantile Plot should match HTML snapshot (if it exists)", () => {
        if (plotInstance.plotOptions.scoreBased) {
          setParam({ plot: plotInstance.plotOptions.scoreBased });

          it.each(
            selectionOptions.filter((selection) => selection.type !== "runset"),
          )("with selection of the type %s", (selection) => {
            setParam({ selection: selection.value });
            plotInstance.refreshUrlState();
            expect(plot).toMatchSnapshot();
          });
        }
      });
    });
  });
