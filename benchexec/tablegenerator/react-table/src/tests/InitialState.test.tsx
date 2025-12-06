// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

// @ts-expect-error TS(6133): 'React' is declared but its value is never read.
import React from "react";
import Overview from "../components/Overview";
// @ts-expect-error TS(7016): Could not find a declaration file for module 'reac... Remove this comment to see the full error message
import renderer from "react-test-renderer";
const fs = require("fs");

const content = fs.readFileSync(
  "../test_integration/expected/big-table.diff.html",
  {
    encoding: "UTF-8",
  },
);
let data = JSON.parse(content);
const initialHref = document.location.href;

describe("Initial state parameter tests", () => {
  describe("leads to right menu item", () => {
    const menuItemPaths = ["/table", "/quantile", "/scatter", "/info"];

    it.each(menuItemPaths)("with initial parameter %s", (parameter) => {
      document.location.href = initialHref;
      data.initial = parameter;

      const overviewInstance = renderer
        // @ts-expect-error TS(2322): Type '{ data: any; }' is not assignable to type 'I... Remove this comment to see the full error message
        .create(<Overview data={data} />)
        .getInstance();

      expect(overviewInstance.state.active).toBe(parameter.substring(1));
    });

    const urlParameters = [
      "hidden0=0",
      "notExisting=notExisting",
      "broken+#--param=<<2893n-s,cn^^",
    ];
    const menuItemPathsWithParameters = menuItemPaths.flatMap((menuItem) =>
      urlParameters.map((urlParam) => menuItem + "?" + urlParam),
    );

    it.each(menuItemPathsWithParameters)(
      "with initial parameter %s",
      (parameter) => {
        document.location.href = initialHref;
        data.initial = parameter;

        const overviewInstance = renderer
          // @ts-expect-error TS(2322): Type '{ data: any; }' is not assignable to type 'I... Remove this comment to see the full error message
          .create(<Overview data={data} />)
          .getInstance();

        const tabToBeActive = parameter.substring(1).split("?")[0];
        expect(overviewInstance.state.active).toBe(tabToBeActive);
      },
    );
  });

  it("shows summary for non-existent menu item", () => {
    document.location.href = initialHref;
    data.initial = "/non-existing";

    const overviewInstance = renderer
      // @ts-expect-error TS(2322): Type '{ data: any; }' is not assignable to type 'I... Remove this comment to see the full error message
      .create(<Overview data={data} />)
      .getInstance();

    expect(overviewInstance.state.active).toBe("summary");
  });

  it("isn't applied if a '#' is added to the URL", () => {
    document.location.href = initialHref + "#";
    data.initial = "/table";

    const overviewInstance = renderer
      // @ts-expect-error TS(2322): Type '{ data: any; }' is not assignable to type 'I... Remove this comment to see the full error message
      .create(<Overview data={data} />)
      .getInstance();

    expect(overviewInstance.state.active).toBe("summary");
  });
});
