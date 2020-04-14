/* SPDX-License-Identifier: Apache-2.0
 *
 * BenchExec is a framework for reliable benchmarking.
 * This file is part of BenchExec.
 * Copyright (C) Dirk Beyer. All rights reserved.
 */
import React from "react";
import TaskDefinitionViewer from "../components/TaskDefinitionViewer.js";
import fs from "fs";
import path from "path";
import { test_multiple_snapshots_of } from "./utils.js";

// mock uniqid to have consistent names
// https://stackoverflow.com/a/44538270/396730
jest.mock("uniqid", () => i => i + "uniqid");

// path where the data for the overview originally came from
const pathToStartFrom = "../test_integration/expected/";

test_multiple_snapshots_of("Render TaskDefinitionViewer", overview => {
  const components = [];

  overview.originalTable.forEach(tableEntry => {
    let content = "";
    const pathToFile = pathToStartFrom + tableEntry.href;

    if (pathToFile.endsWith(".yml") && fs.existsSync(pathToFile)) {
      content = fs.readFileSync(pathToFile, { encoding: "UTF-8" });
      const taskDefinitionViewer = (
        <TaskDefinitionViewer
          yamlText={content}
        />
      );
      components.push(taskDefinitionViewer);
    }
  })
  return components;
});
