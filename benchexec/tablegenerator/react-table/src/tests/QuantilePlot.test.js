// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import React from "react";
import QuantilePlot from "../components/QuantilePlot.js";
import Overview from "../components/Overview";
import renderer from "react-test-renderer";
import { setParam } from "../utils/utils";
const fs = require("fs");

const testDir = "../test_integration/expected/";

fs.readdirSync(testDir)
  .filter((file) => file.endsWith(".html"))
  .filter((file) => fs.statSync(testDir + file).size < 100000)
  .forEach((file) => {
    describe("Quantile Plot tests for " + file, () => {
      const content = fs.readFileSync(testDir + file, { encoding: "UTF-8" });
      const data = JSON.parse(content);
      const overview = renderer.create(<Overview data={data} />).getInstance();
      const quantilePlotJSX = (
        <QuantilePlot
          table={overview.state.table}
          tools={overview.state.tools}
          preSelection={overview.state.quantilePreSelection}
          getRowName={overview.getRowName}
          hiddenCols={overview.state.hiddenCols}
          isFlexible={false}
          fixedWidth={1500}
          fixedHeight={1000}
        />
      );
      const plot = renderer.create(quantilePlotJSX);
      const plotInstance = plot.getInstance();
      const selectionOptions = plot.root
        .findAllByType("select")
        .find((selection) => selection.props.name === "setting-Selection")
        .findAllByType("option")
        .map((option) => option.props.value);

      describe("Quantile Plot should match HTML snapshot", () => {
        plotInstance.setState({ plot: plotInstance.plotOptions.quantile });

        it.each(selectionOptions)("with selection %s", (option) => {
          setParam({ selection: option });
          plotInstance.refreshUrlState();
          expect(plot).toMatchSnapshot();
        });
      });

      describe("Direct Plot should match HTML snapshot", () => {
        plotInstance.setState({ plot: plotInstance.plotOptions.direct });

        it.each(selectionOptions)("with selection %s", (option) => {
          setParam({ selection: option });
          plotInstance.refreshUrlState();
          expect(plot).toMatchSnapshot();
        });
      });

      describe("Score-based Quantile Plot should match HTML snapshot if it exists", () => {
        if (plotInstance.plotOptions.scoreBased) {
          plotInstance.setState({ plot: plotInstance.plotOptions.scoreBased });

          it.each(selectionOptions)("with selection %s", (option) => {
            setParam({ selection: option });
            plotInstance.refreshUrlState();
            expect(plot).toMatchSnapshot();
          });
        }
      });
    });
  });
