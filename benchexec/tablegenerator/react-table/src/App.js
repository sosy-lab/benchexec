/* SPDX-License-Identifier: Apache-2.0
 *
 * BenchExec is a framework for reliable benchmarking.
 * This file is part of BenchExec.
 * Copyright (C) Dirk Beyer. All rights reserved.
 */
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
          <Overview data={window.data} />
          {/* imports the component Overview with all subcomponents */}
        </main>
      </div>
    );
  }
}

export default App;
