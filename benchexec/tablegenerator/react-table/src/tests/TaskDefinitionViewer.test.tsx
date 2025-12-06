// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

// @ts-expect-error TS(6133): 'React' is declared but its value is never read.
import React from "react";
import TaskDefinitionViewer from "../components/TaskDefinitionViewer.js";
import fs from "fs";
// @ts-expect-error TS(7016): Could not find a declaration file for module 'reac... Remove this comment to see the full error message
import renderer from "react-test-renderer";

const testDir = "src/tests/task_definition_files/";

fs.readdirSync(testDir)
  .filter((file) => file.endsWith(".yml"))
  .forEach((file) => {
    it("Render TaskDefinitionViewer for " + file, () => {
      // @ts-expect-error TS(2769): No overload matches this call.
      const content = fs.readFileSync(testDir + file, { encoding: "UTF-8" });
      const component = renderer.create(
        <TaskDefinitionViewer
          // @ts-expect-error TS(2322): Type '{ yamlText: Buffer & string; createHref: (fi... Remove this comment to see the full error message
          yamlText={content}
          createHref={(fileUrl: any) => fileUrl}
        />,
      );
      expect(component).toMatchSnapshot();
    });
  });
