/* SPDX-License-Identifier: Apache-2.0
 *
 * BenchExec is a framework for reliable benchmarking.
 * This file is part of BenchExec.
 * Copyright (C) Dirk Beyer. All rights reserved.
 */
import "./App.scss";
import React, {Component} from "react";
import Overview from "./components/Overview";

if (process.env.NODE_ENV !== "production") {
  // load example data for development
  // eslint-disable-next-line global-require, import/no-unresolved
  window.data = require("@data");
  window.data.version = "(development build)";
}

class App extends Component {
  // eslint-disable-next-line class-methods-use-this
  render() {
    return (
      <div className="App">
        <main>
          <Overview data={window.data} />
          {/* imports the component Overview with all subcomponents */}
        </main>
        <footer className="App-footer"></footer>
      </div>
    );
  }
}

export default App;
