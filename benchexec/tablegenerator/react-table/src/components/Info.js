// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import React from "react";

const dependencies = require("../data/dependencies.json");

class Dependency extends React.Component {
  knownLicenses = ["BSD-3-Clause", "CC-BY-4.0", "ISC", "MIT", "Zlib"];
  linkifyLicense = (license) => (
    <a
      key={license}
      href={"https://spdx.org/licenses/" + license}
      target="_blank"
      rel="noopener noreferrer"
    >
      {license}
    </a>
  );
  linkifyLicenses = (licensesString) =>
    licensesString
      .split(/([A-Za-z0-9.-]+)/)
      .map((s) =>
        this.knownLicenses.includes(s) ? this.linkifyLicense(s) : s,
      );

  render = () => (
    <div>
      <h4>
        <a
          href={
            "https://www.npmjs.com/package/" +
            this.props.name +
            "/v/" +
            this.props.version
          }
          target="_blank"
          rel="noopener noreferrer"
        >
          {this.props.name} {this.props.version}
        </a>
      </h4>
      {this.props.repository && (
        <>
          Source:{" "}
          <a
            href={this.props.repository}
            target="_blank"
            rel="noopener noreferrer"
          >
            {this.props.repository}
          </a>
          <br />
        </>
      )}
      {this.props.copyright && (
        <>
          {this.props.copyright}
          <br />
        </>
      )}
      License: <>{this.linkifyLicenses(this.props.licenses)}</>
      {this.props.licenseId !== undefined && (
        <>
          <br />
          <details>
            <summary>Full text of license</summary>
            <pre>{dependencies.licenses[this.props.licenseId]}</pre>
          </details>
        </>
      )}
    </div>
  );
}

const Info = (props) => (
  <div className="info">
    <div className="info-header">
      <h1>Info and Help</h1>
    </div>
    <h3>Summary</h3>
    <ul>
      <li>Shows environment information and a summary of the results.</li>
      <li>
        <strong>Select columns:</strong> <br /> The columns to show can be
        selected by clicking on <em>Click here to select columns</em> or{" "}
        <span className="link" onClick={props.selectColumn}>
          here
        </span>
        .
      </li>
      <li>
        <strong>Quantile plot:</strong> <br />A quantile plot for a column can
        be shown by clicking on the respective column header (e.g.,{" "}
        <em>cputime</em>).
      </li>
      <li>
        <strong>Fixed row title:</strong> <br />
        Deselect to let the left-most column scroll together with the rest of
        the table.
      </li>
    </ul>
    <h3>Table</h3>
    <ul>
      <li>Shows the detailed results.</li>
      <li>
        <strong>Fixed task:</strong> <br />
        Deselect to let the left-most column with the task name scroll together
        with the rest of the table.
      </li>
      <li>
        <strong>Select columns:</strong> <br /> The columns to show can be
        selected by clicking on <em>Click here to select columns</em> or{" "}
        <span className="link" onClick={props.selectColumn}>
          here
        </span>
        .
      </li>
      <li>
        <strong>Filter rows:</strong> <br />
        Filters can be applied to every column in the row below the column
        header. Numeric columns accept a range filter like <em>min:max</em>,
        where both <em>min</em> and <em>max</em> are numeric values that can
        also be omitted for half-open ranges. For text columns (like the task
        name) any row matches that contains the entered filter value. Several
        filters can be combined and will be applied together. All filters can be
        deleted at once with the <em>Reset Filters</em> button in the top right
        corner.
      </li>
      <li>
        <strong>Sort rows:</strong> <br /> Rows can be sorted by clicking on the
        column header. Clicking again will toggle the sort order (ascending vs.
        descending). Hold <kbd>Shift</kbd> while clicking for adding a column to
        the sort order.
      </li>
      <li>
        <strong>Tool output:</strong> <br />
        Clicking on a cell in the status column will show the tool output of
        this run.
      </li>
      <li>
        <strong>Task definition:</strong> <br /> Clicking on the task name will
        show the content of the respective file.
      </li>
    </ul>
    <h3> Quantile Plot and Scatter Plot</h3>
    <ul>
      <li>
        Shows plots of the results that are currently visible in the table.
      </li>
      <li>
        <strong>Correct results only:</strong> <br />
        In addition to the currently applied filter, the plots by default show
        only correct results. Click <em>Switch to All Results</em> to toggle
        this behavior.
      </li>
      <li>
        <strong>Select columns:</strong>
        <br />
        The drop-down fields above the plots allow to choose which columns are
        shown in the plot.
      </li>
    </ul>
    <h3>About</h3>
    <p>
      This table was generated by{" "}
      <a
        className="link"
        href="https://github.com/sosy-lab/benchexec"
        target="_blank"
        rel="noopener noreferrer"
      >
        BenchExec {props.version}
      </a>
      . For feedback, questions, and bug reports please use our{" "}
      <a
        className="link"
        href="https://github.com/sosy-lab/benchexec/issues?q=is%3Aissue+is%3Aopen+sort%3Aupdated-desc+label%3A%22HTML+table%22"
        target="_blank"
        rel="noopener noreferrer"
      >
        issue tracker
      </a>
      .
    </p>
    <p>
      License:{" "}
      <a
        className="link"
        href="https://www.apache.org/licenses/LICENSE-2.0"
        target="_blank"
        rel="noopener noreferrer"
      >
        Apache 2.0 License
      </a>
    </p>
    <details>
      <summary>
        This application includes third-party dependencies under different
        licenses. Click here to view them.
      </summary>
      {dependencies.dependencies.map((dependency) => {
        return (
          <Dependency
            key={dependency.name + dependency.version}
            {...dependency}
          />
        );
      })}
    </details>
  </div>
);
export default Info;
