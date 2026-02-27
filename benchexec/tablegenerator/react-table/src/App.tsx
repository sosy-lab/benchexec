// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import "./App.scss";
import React from "react";
import Overview from "./components/Overview";

// ==============================
// Global augmentations
// ==============================

declare global {
  interface Window {
    // Global injected app data (loaded via @data in dev and via index.html in prod).
    data: unknown;
  }
}

// ==============================
// Component props
// ==============================

interface AppProps {
  // Callback that is forwarded to Overview. We keep it generic here
  // because the exact payload type is defined by Overview.
  onStatsReady?: (stats: unknown) => void;
}

if (process.env.NODE_ENV !== "production") {
  // Load example data for development
  // `require` is used here intentionally because @data is only available in dev builds.
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  window.data = require("@data") as unknown;

  // `window.data` is `unknown` on purpose (shape depends on runtime data).
  // We keep the original behavior and only narrow locally for this assignment.
  (window.data as { version?: string }).version = "(development build)";
}

const App = (props: AppProps): JSX.Element => {
  // If we visit this page without a hash, like www.domain.com/ or www.domain.com/subpage, we
  // append a hash to the URL to ensure that the page is loaded correctly. This is necessary
  // to ensure correct routing in the app.
  if (window.location.hash === "") {
    window.location.hash = "#/";
  }

  return (
    <div className="App">
      <main>
        <Overview
          data={window.data}
          renderPlotsFlexible={true}
          onStatsReady={props.onStatsReady}
        />
        {/*
         * Imports the component Overview with all subcomponents.
         * The renderPlotsFlexible prop should always be true in development and production,
         * but will be set to false in the tests to make them work.
         */}
      </main>
    </div>
  );
};

export default App;
