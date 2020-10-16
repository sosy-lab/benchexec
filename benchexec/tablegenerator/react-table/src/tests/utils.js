// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import React from "react";
import ReactDOM from "react-dom";
import renderer from "react-test-renderer";
import Overview from "../components/Overview";
import {
  prepareTableData,
  getRawOrDefault,
  getTaskIdParts,
  createHiddenColsFromURL,
} from "../utils/utils";

import {
  getFilterableData,
  buildMatcher,
  applyMatcher,
} from "../utils/filters";
const fs = require("fs");

// We use jest snapshots for integration tests, and they become quite large.
// It is not really recommended by jest to do this, but this still seems like
// the best option for us. So at least we apply some custom serializers that
// help shrink the size and reduce irrelevant syntactic differences.

// Top-level serializer that does post-processing on the final string
expect.addSnapshotSerializer({
  print: (val, serialize) =>
    serialize(val.toJSON())
      .split("\n")
      // filter empty lines
      .filter((s) => !s.match(/^ *$/))
      // filter handler attributes (nothing important visible)
      .filter((s) => !s.match(/^ *on[a-zA-Z]*=\{\[Function\]\}$/))
      // reduce indentation to one space
      .map((s) => {
        const trimmed = s.trimStart();
        return " ".repeat((s.length - trimmed.length) / 2) + trimmed;
      })
      .join("\n"),
  test: (val) => val && val.hasOwnProperty("toJSON"),
});

// Serializer that simplifies HTML elements with several children,
// if all children are strings by joining the strings (better readable)
expect.addSnapshotSerializer({
  print: (val, serialize) => {
    val.children = [val.children.filter((s) => !s.match(/^ *$/)).join("")];
    return serialize(val);
  },
  test: (val) =>
    val &&
    Array.isArray(val.children) &&
    val.children.length > 1 &&
    val.children.every((o) => typeof o === "string"),
});

// Serializer that simplifies HTML elements with one empty child
// (normalizes <div></div> to <div />)
expect.addSnapshotSerializer({
  print: (val, serialize) => {
    delete val.children;
    return serialize(val);
  },
  test: (val) =>
    val &&
    Array.isArray(val.children) &&
    val.children.length === 1 &&
    !val.children[0],
});

// Serializer that simplies the dangerouslySetInnerHTML attribute
expect.addSnapshotSerializer({
  print: (val, serialize) => serialize(val.__html),
  test: (val) => val && val.hasOwnProperty("__html"),
});

// Serializer that hides empty style attributes.
expect.addSnapshotSerializer({
  print: (val, serialize) => {
    delete val.props.style;
    return serialize(val);
  },
  test: (val) =>
    val &&
    val.props &&
    val.props.style &&
    val.props.style.constructor === Object &&
    Object.keys(val.props.style).length === 0,
});

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
  const {
    tableHeader,
    taskIdNames,
    tools,
    columns,
    table,
    stats,
  } = prepareTableData(data);

  const findAllValuesOfColumn = (columnFilter, valueAccessor) =>
    tools.map((tool, j) =>
      tool.columns.map((column, i) => {
        if (!columnFilter(tool, column)) {
          return undefined;
        }
        const values = table
          .map((row) => valueAccessor(row.results[j], row.results[j].values[i]))
          .filter(Boolean);
        return [...new Set(values)].sort();
      }),
    );

  const filterable = getFilterableData(data);
  const originalTable = table;
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
    table,
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

const getPlotOptions = (plot, options) =>
  plot.root
    .findAllByType("select")
    .find((selection) => selection.props.name === "setting-" + options)
    .findAllByType("option")
    .filter((option) => !option.disabled)
    .map((option) => option.props.value);

export { test_snapshot_of, getPlotOptions, test_snapshot_of_async };
