// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import React from "react";
import TaskDefinitionViewer from "../components/TaskDefinitionViewer.js";
import fs from "fs";
import renderer from "react-test-renderer";

const testDir = "src/tests/task_definition_files/";

fs.readdirSync(testDir)
  .filter((file) => file.endsWith(".yml"))
  .forEach((file) => {
    it("Render TaskDefinitionViewer for " + file, () => {
      const content = fs.readFileSync(testDir + file, { encoding: "UTF-8" });
      const component = renderer.create(
        <TaskDefinitionViewer
          yamlText={content}
          createHref={(fileUrl) => fileUrl}
        />,
      );
      expect(component).toMatchSnapshot();
    });
  });
