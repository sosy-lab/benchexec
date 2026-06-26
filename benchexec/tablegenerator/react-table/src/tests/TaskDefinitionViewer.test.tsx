// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import React from "react";
import TaskDefinitionViewer from "../components/TaskDefinitionViewer";
import fs from "fs";
import * as renderer from "react-test-renderer";

const testDir = "src/tests/task_definition_files/";

type TaskDefinitionViewerProps = React.ComponentProps<
  typeof TaskDefinitionViewer
>;

fs.readdirSync(testDir)
  .filter((file) => file.endsWith(".yml"))
  .forEach((file) => {
    it("Render TaskDefinitionViewer for " + file, () => {
      const content = fs.readFileSync(testDir + file, { encoding: "utf-8" });
      const component = renderer.create(
        <TaskDefinitionViewer
          {...({
            yamlText: content,
            createHref: (fileUrl: string) => fileUrl,
          } as Partial<TaskDefinitionViewerProps> as TaskDefinitionViewerProps)}
        />,
      );

      expect(component).toMatchSnapshot();
    });
  });
