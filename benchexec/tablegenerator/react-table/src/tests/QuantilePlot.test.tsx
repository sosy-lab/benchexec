// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

// @ts-expect-error TS(6133): 'React' is declared but its value is never read.
import React from "react";
import QuantilePlot from "../components/QuantilePlot.js";
import Overview from "../components/Overview";
// @ts-expect-error TS(7016): Could not find a declaration file for module 'reac... Remove this comment to see the full error message
import renderer from "react-test-renderer";
import { constructHashURL } from "../utils/utils";
const fs = require("fs");

/*
 * A testing utility function to set the URL parameters for the test.
 * This is used instead of the setURLParameter function from the utils.js file
 * because the latter doesn't work well with the react-test-renderer.
 *
 * @param {Object} params - The parameters to set in the URL
 * @returns {void}
 */
const updateURLParams = (params: any) => {
  const { newUrl } = constructHashURL(window.location.href, params);
  window.history.pushState({}, "Quantile Plot Test", newUrl);
};

const testDir = "../test_integration/expected/";
const files = ["big-table.diff.html", "rows-with-scores.html"];
files
  .map((fileName) => ({
    fileName,
    content: fs.readFileSync(testDir + fileName, {
      encoding: "UTF-8",
    }),
  }))
  .forEach((fileData) => {
    describe("Quantile Plot tests for file " + fileData.fileName, () => {
      const data = JSON.parse(fileData.content);
      const overviewInstance = renderer
        // @ts-expect-error TS(2322): Type '{ data: any; }' is not assignable to type 'I... Remove this comment to see the full error message
        .create(<Overview data={data} />)
        .getInstance();

      // Fixed width and height because the FlexibleXYPlot doesn't work well with the react-test-renderer
      const quantilePlotJSX = (
        <QuantilePlot
          // @ts-expect-error TS(2322): Type '{ table: any; tools: any; preSelection: any;... Remove this comment to see the full error message
          table={overviewInstance.state.tableData}
          tools={overviewInstance.state.tools}
          preSelection={overviewInstance.state.quantilePreSelection}
          getRowName={overviewInstance.getRowName}
          hiddenCols={overviewInstance.state.hiddenCols}
          isFlexible={false}
        />
      );
      const plot = renderer.create(quantilePlotJSX);
      const plotInstance = plot.getInstance();

      const typesOfCols = plotInstance.possibleValues.map(
        (col: any) => col.type,
      );
      /* Objects of all first occuring columns with an unique type attribute as well as all runsets.
         Overriding of toString() method is used for better identifying test cases. */
      const selectionOptions = plotInstance.possibleValues
        .filter(
          // @ts-expect-error TS(6133): 'self' is declared but its value is never read.
          (col: any, index: any, self: any) =>
            typesOfCols.indexOf(col.type) === index,
        )
        .map((col: any) => ({
          value: col.display_title,
          toString: () => col.type,
        }))
        .concat(
          plotInstance.props.tools.map((tool: any) => ({
            value: "runset-" + tool.toolIdx,
            toString: () => "runset",
          })),
        );
      const resultOptions = Object.values(plotInstance.resultsOptions);

      // Array of pairs of selection and shown results as test data
      const selectionResultInput = selectionOptions.flatMap((selection: any) =>
        resultOptions.map((result) => [selection, result]),
      );

      describe("Quantile Plot should match HTML snapshot", () => {
        updateURLParams({ plot: plotInstance.plotOptions.quantile });

        it.each(selectionResultInput)(
          "with selection of the type %s and %s results",
          // @ts-expect-error TS(2345): Argument of type '(selection: any, results: any) =... Remove this comment to see the full error message
          (selection, results) => {
            updateURLParams({ selection: selection.value, results });

            plotInstance.refreshUrlState();
            expect(plot).toMatchSnapshot();
          },
        );
      });

      describe("Direct Plot should match HTML snapshot", () => {
        updateURLParams({ plot: plotInstance.plotOptions.direct });

        it.each(selectionResultInput)(
          "with selection of the type %s and %s results",
          // @ts-expect-error TS(2345): Argument of type '(selection: any, results: any) =... Remove this comment to see the full error message
          (selection, results) => {
            updateURLParams({ selection: selection.value, results });

            plotInstance.refreshUrlState();
            expect(plot).toMatchSnapshot();
          },
        );
      });

      // Score based plot isn't available if the data doesn't support a scoring scheme
      if (plotInstance.plotOptions.scoreBased) {
        describe("Score-based Quantile Plot should match HTML snapshot (if it exists)", () => {
          updateURLParams({ plot: plotInstance.plotOptions.scoreBased });

          // Only test with columns as runsets can't be selected for score-based plots
          it.each(
            selectionOptions.filter(
              (selection: any) => selection.toString() !== "runset",
            ),
            // @ts-expect-error TS(2345): Argument of type '(selection: any) => void' is not... Remove this comment to see the full error message
          )("with selection of the type %s", (selection) => {
            updateURLParams({ selection: selection.value });

            plotInstance.refreshUrlState();
            expect(plot).toMatchSnapshot();
          });
        });
      }
    });
  });
