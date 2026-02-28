// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import ReactDOM from "react-dom";
import * as renderer from "react-test-renderer";
import {
  prepareTableData,
  getRawOrDefault,
  createHiddenColsFromURL,
} from "../utils/utils";

import { getFilterableData } from "../utils/filters";
import fs from "fs";

import React from "react";
import Table from "../components/ReactTable";
import SelectColumn from "../components/SelectColumn";
import StatisticsTable from "../components/StatisticsTable";

const testDir = "../test_integration/expected/";

/* ============================================================
 * Types
 * ============================================================ */

type TableProps = React.ComponentProps<typeof Table>;
type SelectColumnProps = React.ComponentProps<typeof SelectColumn>;
type StatisticsTableProps = React.ComponentProps<typeof StatisticsTable>;

type OverviewTools = TableProps["tools"] extends SelectColumnProps["tools"]
  ? SelectColumnProps["tools"]
  : TableProps["tools"];

type HiddenCols =
  TableProps["hiddenCols"] extends SelectColumnProps["hiddenCols"]
    ? SelectColumnProps["hiddenCols"]
    : TableProps["hiddenCols"];

type Stats = TableProps["stats"] extends StatisticsTableProps["stats"]
  ? StatisticsTableProps["stats"]
  : TableProps["stats"];

type PreparedTableData = ReturnType<typeof prepareTableData>;
type PreparedTools = PreparedTableData["tools"];
type PreparedTableDataRows = PreparedTableData["tableData"];
type PreparedTableHeader = PreparedTableData["tableHeader"];
type PreparedColumns = PreparedTableData["columns"];
type PreparedTaskIdNames = PreparedTableData["taskIdNames"];

type OverviewProps = {
  taskIdNames: PreparedTaskIdNames;
  columns: PreparedColumns;
  tableData: PreparedTableDataRows;
  filteredData: unknown[];
  filterable: ReturnType<typeof getFilterableData>;
  tableHeader: PreparedTableHeader;
  originalTable: PreparedTableDataRows;
  originalTools: PreparedTools;
  data: {
    version: string;
  };
  statusValues: unknown;
  categoryValues: unknown;
  filtered: unknown[];

  toggleSelectColumns: TableProps["selectColumn"];
  prepareTableValues: TableProps["prepareTableValues"];
  setFilter: TableProps["setFilter"];
  filterPlotData: TableProps["filterPlotData"];
  toggleLinkOverlay: TableProps["toggleLinkOverlay"];
  changeTab: TableProps["changeTab"];

  tools: OverviewTools;
  hiddenCols: HiddenCols;

  switchToQuantile: StatisticsTableProps["switchToQuantile"];
  stats: Stats;
};

type ComponentFuncResult = {
  component: React.ReactElement;
  promise: Promise<unknown>;
};

type ComponentFuncAsync = (overview: OverviewProps) => ComponentFuncResult;
type ComponentFuncSync = (overview: OverviewProps) => React.ReactElement;

/* ============================================================
 * Portal override
 * ============================================================ */

// Provide a way to render children into a DOM node that exists outside the hierarchy of the DOM component
ReactDOM.createPortal = ((dom: unknown) =>
  dom) as unknown as typeof ReactDOM.createPortal;

/**
 * Function to get all props that can be passed by the Overview component to its
 * children, without invoking a render
 * @param {object} data
 */
const getOverviewProps = (data: unknown): OverviewProps => {
  const { tableHeader, taskIdNames, tools, columns, tableData, stats } =
    prepareTableData(data as Parameters<typeof prepareTableData>[0]);

  const findAllValuesOfColumn = (
    columnFilter: (
      tool: PreparedTools[number],
      column: PreparedTools[number]["columns"][number],
    ) => boolean,
    valueAccessor: (
      runResult: PreparedTableDataRows[number]["results"][number],
      value: unknown,
    ) => unknown,
  ) =>
    tools.map((tool, j) =>
      tool.columns.map((column, i) => {
        if (!columnFilter(tool, column)) {
          return undefined;
        }
        const values = tableData
          .map((row) => valueAccessor(row.results[j], row.results[j].values[i]))
          .filter(Boolean);
        return [...new Set(values)].sort();
      }),
    );

  const filterable = getFilterableData(
    data as Parameters<typeof getFilterableData>[0],
  );
  const originalTable = tableData;
  const originalTools = tools;

  const filteredData: unknown[] = [];

  const hiddenCols = createHiddenColsFromURL(
    tools as Parameters<typeof createHiddenColsFromURL>[0],
  );

  const statusValues = findAllValuesOfColumn(
    (_tool, column) => column.type === "status",
    (_runResult, value) =>
      getRawOrDefault(
        value as Parameters<typeof getRawOrDefault>[0],
        undefined,
      ),
  );
  const categoryValues = findAllValuesOfColumn(
    (_tool, column) => column.type === "status",
    (runResult) => runResult.category,
  );

  return {
    taskIdNames,
    tools,
    columns,
    tableData,
    filteredData,
    filterable,
    hiddenCols,
    tableHeader,
    stats,
    originalTable,
    originalTools,
    data,
    statusValues,
    categoryValues,
    filtered: [],
  };
};

/**
 * Asynchronous variant of {@link test_snapshot_of} that awaits the resolving
 * of a promise that is returned in the component_func
 *
 * @param {*} name Name of test
 * @param {*} component_func Retrieval function for component
 */
const test_snapshot_of_async = (
  name: string,
  component_func: ComponentFuncAsync,
): void => {
  fs.readdirSync(testDir)
    .filter((file) => file.endsWith(".html"))
    .filter((file) => fs.statSync(`${testDir}${file}`).size < 100000)
    .forEach((file) => {
      it(`${name} for ${file}`, async () => {
        const content = fs.readFileSync(`${testDir}${file}`, {
          encoding: "utf-8",
        });
        const data = JSON.parse(content) as unknown;
        const overview = getOverviewProps(data);
        const { component: c, promise } = component_func(overview);

        let component!: renderer.ReactTestRenderer;

        await renderer.act(async () => {
          component = renderer.create(c);
          await promise;
        });

        expect(component).toMatchSnapshot();
      });
    });
};

const test_snapshot_of = (
  name: string,
  component_func: ComponentFuncSync,
): void => {
  fs.readdirSync(testDir)
    .filter((file) => file.endsWith(".html"))
    .filter((file) => fs.statSync(`${testDir}${file}`).size < 100000)
    .forEach((file) => {
      it(`${name} for ${file}`, () => {
        const content = fs.readFileSync(`${testDir}${file}`, {
          encoding: "utf-8",
        });
        const data = JSON.parse(content) as unknown;

        const overview = getOverviewProps(data);

        const component = renderer.create(component_func(overview));

        expect(component).toMatchSnapshot();
      });
    });
};

export { test_snapshot_of, test_snapshot_of_async, getOverviewProps };
