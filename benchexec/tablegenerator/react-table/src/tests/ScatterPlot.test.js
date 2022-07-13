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
const fs = require("fs");

const content = fs.readFileSync(
  "../test_integration/expected/big-table.diff.html",
  {
    encoding: "UTF-8",
  },
);
const data = JSON.parse(content);
const overviewInstance = renderer
  .create(<Overview data={data} />)
  .getInstance();

// Fixed width and height because the FlexibleXYPlot doesn't work well with the react-test-renderer
const scatterPlotJSX = (
  <ScatterPlot
    table={overviewInstance.state.tableData}
    columns={overviewInstance.columns}
    tools={overviewInstance.state.tools}
    getRowName={overviewInstance.getRowName}
    hiddenCols={overviewInstance.state.hiddenCols}
    isFlexible={false}
  />
);
const plot = renderer.create(scatterPlotJSX);
const plotInstance = plot.getInstance();

// Store a reference of the tool the column belongs to in the column object for later use
const colsWithToolRef = plotInstance.props.tools.flatMap((tool) =>
  tool.columns.map((col) => ({ ...col, toolIdx: tool.toolIdx })),
);

describe("Scatter Plot with columns of same runset should match HTML snapshot", () => {
  /* Objects of all columns of the first runset of the format 0-{colIdx}.
     Overriding of toString() method is used for better identifying test cases. */
  const selectionOptions = plotInstance.props.tools[0].columns.map((col) => ({
    value: "0-" + col.colIdx,
    toString: () => col.display_title,
  }));

  // All combinations of the columns of the first runset with all result options.
  const selectionResultInput = getSelectionResultInput(selectionOptions);

  it.each(selectionResultInput)(
    "with X-Axis %s and Y-Axis %s and %s results",
    (xSelection, ySelection, results) => {
      const params = getSelections(xSelection, ySelection);
      setUrlParams({ ...params, results });
      expect(plot).toMatchSnapshot();
    },
  );
});

describe("Scatter Plot with columns of different runsets should match HTML snapshot", () => {
  const toolIdxesOfCols = colsWithToolRef.map((col) => col.toolIdx);
  /* Objects of all first occuring columns of all runsets of the format {runsetIdx}-{colIdx}.
     Overriding of toString() method is used for better identifying test cases. */
  const selectionOptions = colsWithToolRef
    .filter((col, index) => toolIdxesOfCols.indexOf(col.toolIdx) === index)
    .map((col) => ({
      value: col.toolIdx + "-" + col.colIdx,
      toString: () => col.display_title + " of runset " + col.toolIdx,
    }));

  // All combinations of the first columns of all runsets with all result options.
  const selectionResultInput = getSelectionResultInput(selectionOptions);

  it.each(selectionResultInput)(
    "with X-Axis %s and Y-Axis %s and %s results",
    (xSelection, ySelection, results) => {
      const params = getSelections(xSelection, ySelection);
      setUrlParams({ ...params, results });
      expect(plot).toMatchSnapshot();
    },
  );
});

describe("Scatter Plot with columns of different types should match HTML snapshot", () => {
  const typesOfCols = colsWithToolRef.map((col) => col.type);
  /* Objects of all first occuring columns with an unique type attribute of the format {runsetIdx}-{colIdx}.
     Overriding of toString() method is used for better identifying test cases. */
  const selectionOptions = colsWithToolRef
    .filter((col, index, self) => typesOfCols.indexOf(col.type) === index)
    .map((col) => ({
      value: col.toolIdx + "-" + col.colIdx,
      toString: () => col.type,
    }));

  // All combinations of the first columns of different types with all result options.
  const selectionResultInput = getSelectionResultInput(selectionOptions);

  it.each(selectionResultInput)(
    "with X-Axis of the type %s and Y-Axis of the type %s and %s results",
    (xSelection, ySelection, results) => {
      const params = getSelections(xSelection, ySelection, results);
      setUrlParams({ ...params, results });
      expect(plot).toMatchSnapshot();
    },
  );
});

describe("Scatter Plot linear regression should match HTML snapshot", () => {
  /* Objects of all ordinal columns of all runsets of the format {runsetIdx}-{colIdx}.
     Overriding of toString() method is used for better identifying test cases. */
  const selectionOptions = colsWithToolRef
    .filter(
      (col) => plotInstance.handleType(col.toolIdx, col.colIdx) !== "ordinal",
    )
    .map((col) => ({
      value: col.toolIdx + "-" + col.colIdx,
      toString: () => col.display_title + " of runset " + col.toolIdx,
    }));

  // All paired combinations of all columns.
  const selectionInput = getSelectionInput(selectionOptions);

  it.each(selectionInput)(
    "with X-Axis of the type %s and Y-Axis of the type %s",
    (xSelection, ySelection) => {
      const params = getSelections(xSelection, ySelection);
      setUrlParams({
        ...params,
        regression: plotInstance.regressionOptions.linear,
      });
      expect(plot).toMatchSnapshot();
    },
  );
});

// Creates an array of tuples of the selection for the X-axis and Y-axis
function getSelectionInput(selectionOptions) {
  return selectionOptions.flatMap((xAxis, i) =>
    selectionOptions.slice(i).map((yAxis) => [xAxis, yAxis]),
  );
}

// Creates an array of triples of the selection for the X-axis, Y-axis and shown results as test data
function getSelectionResultInput(selectionOptions) {
  return selectionOptions.flatMap((xAxis, i) =>
    selectionOptions
      .slice(i)
      .flatMap((yAxis) =>
        Object.keys(plotInstance.resultsOptions).map((result) => [
          xAxis,
          yAxis,
          result,
        ]),
      ),
  );
}

function getSelections(xSelection, ySelection) {
  let [toolX, columnX] = xSelection.value.split("-");
  let [toolY, columnY] = ySelection.value.split("-");
  columnX = columnX.replace("___", "-");
  columnY = columnY.replace("___", "-");
  return { toolX, columnX, toolY, columnY };
}

function setUrlParams(params) {
  setParam(params);
  plotInstance.refreshUrlState();
}
