/* SPDX-License-Identifier: Apache-2.0
 *
 * BenchExec is a framework for reliable benchmarking.
 * This file is part of BenchExec.
 * Copyright (C) Dirk Beyer. All rights reserved.
 */
// react standard
import React from "react";
import renderer from "react-test-renderer";

// components
import Overview from "../components/Overview";
import Summary from "../components/Summary.js";

// mock uniqid to have consistent names
// https://stackoverflow.com/a/44538270/396730
jest.mock("uniqid", () => i => i + "uniqid");

it("Render Summary", () => {
  window.data = require("../data/data.json");

  const overview = renderer.create(<Overview />).getInstance();
  const component = renderer
    .create(
      <Summary
        tools={overview.originalTools}
        tableHeader={overview.tableHeader}
        selectColumn={overview.toggleSelectColumns}
        stats={overview.stats}
        prepareTableValues={overview.prepareTableValues}
        getRunSets={overview.getRunSets}
        changeTab={overview.changeTab}
      />
    )
    .toJSON();

  expect(component).toMatchSnapshot();
});
