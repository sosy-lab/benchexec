/* SPDX-License-Identifier: Apache-2.0
 *
 * BenchExec is a framework for reliable benchmarking.
 * This file is part of BenchExec.
 * Copyright (C) Dirk Beyer. All rights reserved.
 */
import React from "react";
import TaskDefinitionViewer from "../components/TaskDefinitionViewer.js";
import fs from "fs";
import renderer from "react-test-renderer";

const testDir = "src/tests/task_definition_files/";

fs.readdirSync(testDir)
  .filter(file => file.endsWith(".yml"))
  .filter(file => fs.statSync(testDir + file).size < 100000)
  .forEach(file => {
    it("Render TaskDefinitionViewer for " + file, () => {
      const content = fs.readFileSync(testDir + file, { encoding: "UTF-8" });
      const component = renderer.create(
        <TaskDefinitionViewer yamlText={content} />,
      );
      expect(component).toMatchSnapshot();
    });
  });
