// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import React from "react";
import ScatterPlot from "../components/ScatterPlot.js";
import Overview from "../components/Overview";
import * as renderer from "react-test-renderer";
import { constructHashURL } from "../utils/utils";
import fs from "fs";

/* ============================================================
 * Types
 * ============================================================ */

type OverviewProps = React.ComponentProps<typeof Overview>;
type OverviewData = OverviewProps["data"];

type ScatterPlotProps = React.ComponentProps<typeof ScatterPlot>;

type OverviewInstance = {
  state: {
    tableData: ScatterPlotProps["table"];
    tools: ScatterPlotProps["tools"];
    hiddenCols: ScatterPlotProps["hiddenCols"];
  };
  columns: ScatterPlotProps["columns"];
  getRowName: ScatterPlotProps["getRowName"];
};

type PlotInstance = {
  props: { tools: Array<{ toolIdx: number; columns: Array<Col> }> };
  resultsOptions: Record<string, unknown>;
  regressionOptions: { linear: string };
  refreshUrlState: () => void;
  handleType: (toolIdx: number, colIdx: string) => string;
};

type Col = {
  colIdx: string;
  display_title: string;
  type?: string;
};

type ColWithToolRef = Col & { toolIdx: number };

type SelectionOption = {
  value: string;
  toString: () => string;
};

type SelectionTuple = [SelectionOption, SelectionOption];
type SelectionResultTuple = [SelectionOption, SelectionOption, string];

/* ============================================================
 * Test setup
 * ============================================================ */

const content = fs.readFileSync(
  "../test_integration/expected/big-table.diff.html",
  {
    encoding: "utf-8",
  },
);

const data = JSON.parse(content) as OverviewData;

const overviewInstance = renderer
  .create(<Overview data={data} />)
  .getInstance() as unknown as OverviewInstance;

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
const plotInstance = plot.getInstance() as unknown as PlotInstance;

// Store a reference of the tool the column belongs to in the column object for later use
const colsWithToolRef: ColWithToolRef[] = plotInstance.props.tools.flatMap(
  (tool) => tool.columns.map((col) => ({ ...col, toolIdx: tool.toolIdx })),
);

describe("Scatter Plot with columns of same runset should match HTML snapshot", () => {
  /* Objects of all columns of the first runset of the format 0-{colIdx}.
     Overriding of toString() method is used for better identifying test cases. */
  const selectionOptions: SelectionOption[] =
    plotInstance.props.tools[0].columns.map((col) => ({
      value: `0-${col.colIdx}`,
      toString: () => col.display_title,
    }));

  // All combinations of the columns of the first runset with all result options.
  const selectionResultInput = getSelectionResultInput(selectionOptions);

  it.each(selectionResultInput)(
    "with X-Axis %s and Y-Axis %s and %s results",
    (
      xSelection: SelectionOption,
      ySelection: SelectionOption,
      results: string,
    ) => {
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
  const selectionOptions: SelectionOption[] = colsWithToolRef
    .filter((col, index) => toolIdxesOfCols.indexOf(col.toolIdx) === index)
    .map((col) => ({
      value: `${col.toolIdx}-${col.colIdx}`,
      toString: () => `${col.display_title} of runset ${col.toolIdx}`,
    }));

  // All combinations of the first columns of all runsets with all result options.
  const selectionResultInput = getSelectionResultInput(selectionOptions);

  it.each(selectionResultInput)(
    "with X-Axis %s and Y-Axis %s and %s results",
    (
      xSelection: SelectionOption,
      ySelection: SelectionOption,
      results: string,
    ) => {
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
  const selectionOptions: SelectionOption[] = colsWithToolRef
    .filter((col, index) => typesOfCols.indexOf(col.type) === index)
    .map((col) => ({
      value: `${col.toolIdx}-${col.colIdx}`,
      toString: () => String(col.type),
    }));

  // All combinations of the first columns of different types with all result options.
  const selectionResultInput = getSelectionResultInput(selectionOptions);

  it.each(selectionResultInput)(
    "with X-Axis of the type %s and Y-Axis of the type %s and %s results",
    (
      xSelection: SelectionOption,
      ySelection: SelectionOption,
      results: string,
    ) => {
      const params = getSelections(xSelection, ySelection);
      setUrlParams({ ...params, results });
      expect(plot).toMatchSnapshot();
    },
  );
});

describe("Scatter Plot linear regression should match HTML snapshot", () => {
  /* Objects of all ordinal columns of all runsets of the format {runsetIdx}-{colIdx}.
     Overriding of toString() method is used for better identifying test cases. */
  const selectionOptions: SelectionOption[] = colsWithToolRef
    .filter(
      (col) => plotInstance.handleType(col.toolIdx, col.colIdx) !== "ordinal",
    )
    .map((col) => ({
      value: `${col.toolIdx}-${col.colIdx}`,
      toString: () => `${col.display_title} of runset ${col.toolIdx}`,
    }));

  // All paired combinations of all columns.
  const selectionInput = getSelectionInput(selectionOptions);

  it.each(selectionInput)(
    "with X-Axis of the type %s and Y-Axis of the type %s",
    (xSelection: SelectionOption, ySelection: SelectionOption) => {
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
function getSelectionInput(
  selectionOptions: SelectionOption[],
): SelectionTuple[] {
  return selectionOptions.flatMap((xAxis, i) =>
    selectionOptions.slice(i).map((yAxis): SelectionTuple => [xAxis, yAxis]),
  );
}

// Creates an array of triples of the selection for the X-axis, Y-axis and shown results as test data
function getSelectionResultInput(
  selectionOptions: SelectionOption[],
): SelectionResultTuple[] {
  return selectionOptions.flatMap((xAxis, i) =>
    selectionOptions
      .slice(i)
      .flatMap((yAxis) =>
        Object.keys(plotInstance.resultsOptions).map(
          (result): SelectionResultTuple => [xAxis, yAxis, result],
        ),
      ),
  );
}

function getSelections(
  xSelection: SelectionOption,
  ySelection: SelectionOption,
): {
  toolX: string;
  columnX: string;
  toolY: string;
  columnY: string;
} {
  const [toolX, columnXRaw] = xSelection.value.split("-");
  const [toolY, columnYRaw] = ySelection.value.split("-");

  const columnX = columnXRaw.replace("___", "-");
  const columnY = columnYRaw.replace("___", "-");

  return { toolX, columnX, toolY, columnY };
}

function setUrlParams(
  params: Record<string, string | number | undefined>,
): void {
  const { newUrl } = constructHashURL(window.location.href, params);
  window.history.pushState({}, "Quantile Plot Test", newUrl);
  plotInstance.refreshUrlState();
}
