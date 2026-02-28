// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import ReactDOM from "react-dom";
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
ReactDOM.createPortal = (dom) => {
  return dom;
};

/**
 * Function to get all props that can be passed by the Overview component to its
 * children, without invoking a render
 * @param {object} data
 */
const getOverviewProps = (data) => {
  const { tableHeader, taskIdNames, tools, columns, tableData, stats } =
    prepareTableData(data);

  const findAllValuesOfColumn = (columnFilter, valueAccessor) =>
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

  const filterable = getFilterableData(data);
  const originalTable = tableData;
  const originalTools = tools;

  const filteredData = [];

  const hiddenCols = createHiddenColsFromURL(tools);

  const statusValues = findAllValuesOfColumn(
    (_tool, column) => column.type === "status",
    (_runResult, value) => getRawOrDefault(value),
  );
  const categoryValues = findAllValuesOfColumn(
    (_tool, column) => column.type === "status",
    (runResult, _value) => runResult.category,
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
const test_snapshot_of_async = (name, component_func) => {
  fs.readdirSync(testDir)
    .filter((file) => file.endsWith(".html"))
    .filter((file) => fs.statSync(testDir + file).size < 100000)
    .forEach((file) => {
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

const test_snapshot_of = (name, component_func) => {
  fs.readdirSync(testDir)
    .filter((file) => file.endsWith(".html"))
    .filter((file) => fs.statSync(testDir + file).size < 100000)
    .forEach((file) => {
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
