// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import ReactDOM from "react-dom";
// @ts-expect-error TS(7016): Could not find a declaration file for module 'reac... Remove this comment to see the full error message
import renderer from "react-test-renderer";
import {
  prepareTableData,
  getRawOrDefault,
  createHiddenColsFromURL,
} from "../utils/utils";

import { getFilterableData } from "../utils/filters";
const fs = require("fs");

const testDir = "../test_integration/expected/";

// Provide a way to render children into a DOM node that exists outside the hierarchy of the DOM component
// @ts-expect-error TS(2322): Type '(dom: ReactNode) => ReactNode' is not assign... Remove this comment to see the full error message
ReactDOM.createPortal = (dom) => {
  return dom;
};

/**
 * Function to get all props that can be passed by the Overview component to its
 * children, without invoking a render
 * @param {object} data
 */
const getOverviewProps = (data: any) => {
  const { tableHeader, taskIdNames, tools, columns, tableData, stats } =
    prepareTableData(data);

  const findAllValuesOfColumn = (columnFilter: any, valueAccessor: any) =>
    tools.map((tool: any, j: any) =>
      tool.columns.map((column: any, i: any) => {
        if (!columnFilter(tool, column)) {
          return undefined;
        }
        const values = tableData
          .map((row: any) =>
            valueAccessor(row.results[j], row.results[j].values[i]),
          )
          .filter(Boolean);
        return [...new Set(values)].sort();
      }),
    );

  const filterable = getFilterableData(data);
  const originalTable = tableData;
  const originalTools = tools;

  const filteredData: any = [];

  const hiddenCols = createHiddenColsFromURL(tools);

  const statusValues = findAllValuesOfColumn(
    (_tool: any, column: any) => column.type === "status",
    // @ts-expect-error TS(2554): Expected 2 arguments, but got 1.
    (_runResult: any, value: any) => getRawOrDefault(value),
  );
  const categoryValues = findAllValuesOfColumn(
    (_tool: any, column: any) => column.type === "status",
    (runResult: any, _value: any) => runResult.category,
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
const test_snapshot_of_async = (name: any, component_func: any) => {
  fs.readdirSync(testDir)
    .filter((file: any) => file.endsWith(".html"))
    .filter((file: any) => fs.statSync(testDir + file).size < 100000)
    .forEach((file: any) => {
      it(name + " for " + file, async () => {
        const content = fs.readFileSync(testDir + file, { encoding: "UTF-8" });
        const data = JSON.parse(content);
        const overview = getOverviewProps(data);
        const { component: c, promise } = component_func(overview);

        let component;

        await renderer.act(async () => {
          component = renderer.create(c);
          await promise;
        });

        expect(component).toMatchSnapshot();
      });
    });
};

const test_snapshot_of = (name: any, component_func: any) => {
  fs.readdirSync(testDir)
    .filter((file: any) => file.endsWith(".html"))
    .filter((file: any) => fs.statSync(testDir + file).size < 100000)
    .forEach((file: any) => {
      it(name + " for " + file, () => {
        const content = fs.readFileSync(testDir + file, { encoding: "UTF-8" });
        const data = JSON.parse(content);

        const overview = getOverviewProps(data);

        const component = renderer.create(component_func(overview));

        expect(component).toMatchSnapshot();
      });
    });
};

export { test_snapshot_of, test_snapshot_of_async, getOverviewProps };
