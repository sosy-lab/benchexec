// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import "./App.scss";
import React, { Component } from "react";
import Overview from "./components/Overview";

if (process.env.NODE_ENV !== "production") {
  // load example data for development
  window.data = require("@data");
  window.data.version = "(development build)";
}

class App extends Component {
  render() {
    return (
      <div className="App">
        <main>
          <Overview data={window.data} renderPlotsFlexible={true} />
          {/* imports the component Overview with all subcomponents.
              The renderPlotsFlexible prop should always be true in development and production, but will be set to false in the tests to make them work.*/}
        </main>
      </div>
    );
  }
}

export default App;
