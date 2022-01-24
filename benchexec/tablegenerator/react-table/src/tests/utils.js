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
const fs = require("fs");

const testDir = "../test_integration/expected/";

// Provide a way to render children into a DOM node that exists outside the hierarchy of the DOM component
ReactDOM.createPortal = (dom) => {
  return dom;
};

const test_snapshot_of = (name, component_func) => {
  fs.readdirSync(testDir)
    .filter((file) => file.endsWith(".html"))
    .filter((file) => fs.statSync(testDir + file).size < 100000)
    .forEach((file) => {
      it(name + " for " + file, () => {
        const content = fs.readFileSync(testDir + file, { encoding: "UTF-8" });
        const data = JSON.parse(content);

        const overview = renderer
          .create(<Overview data={data} />)
          .getInstance();
        const component = renderer.create(component_func(overview));

        expect(component).toMatchSnapshot();
      });
    });
};

export { test_snapshot_of };
