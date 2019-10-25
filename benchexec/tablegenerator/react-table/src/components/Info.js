/* SPDX-License-Identifier: Apache-2.0
 *
 * BenchExec is a framework for reliable benchmarking.
 * This file is part of BenchExec.
 * Copyright (C) Dirk Beyer. All rights reserved.
 */
import React from "react";

const dependencies = require("../data/dependencies.json");

class Dependency extends React.Component {
  knownLicenses = ["BSD-3-Clause", "CC-BY-4.0", "ISC", "MIT", "Zlib"];
  linkifyLicense = license => (
    <a
      key={license}
      href={"https://spdx.org/licenses/" + license}
      target="_blank"
      rel="noopener noreferrer"
    >
      {license}
    </a>
  );
  linkifyLicenses = licensesString =>
    licensesString
      .split(/([A-Za-z0-9.-]+)/)
      .map(s => (this.knownLicenses.includes(s) ? this.linkifyLicense(s) : s));

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
      <br />
      <details>
        <summary>Full text of license</summary>
        <pre>{dependencies.licenses[this.props.licenseId]}</pre>
      </details>
    </div>
  );
}

export default props => (
  <div className="info">
    <div className="info-header">
      <h1>Info and Help</h1>
    </div>
    <h3>Summary:</h3>
    <ul>
      <li>
        Find your environment information and the summary which was on the
        bottom of the table
      </li>
      <li>
        <strong>Select columns:</strong> <br /> To customize your columns, click
        on the field on the left side "Click here to select columns" or{" "}
        <span className="link" onClick={props.selectColumn}>
          here
        </span>
        .
      </li>
      <li>
        <strong>Link to quantile plot:</strong> <br />
        With a click on the column-title you are leaded directly to the
        corresponding quantile plot
      </li>
      <li>
        <strong>Fixed task</strong> <br />
        Deselect the box to scroll horizontal in the hole table, select it to
        scroll only in the results. The tasks will be fixed on the left side.{" "}
      </li>
    </ul>
    <h3>Table: </h3>
    <ul>
      <li>
        <strong>Fixed task</strong> <br />
        Deselect the box to scroll horizontal in the hole table, select it to
        scroll only in the results. The tasks will be fixed on the left side.{" "}
      </li>
      <li>
        <strong>Select columns:</strong> <br /> To customize your columns, click
        on the field on the left side "Click here to select columns" or{" "}
        <span className="link" onClick={props.selectColumn}>
          here
        </span>
        .
      </li>
      <li>
        <strong>Horizontally scrolling:</strong> <br />
        To scroll horizontally through the hole table deselect the checkbox
        "Fixed task" above the selected columns.
      </li>
      <li>
        <strong>Filtering:</strong> <br /> You can filter every row on the top
        of it. Write the your maximum like ":n", your minimum like "n:", minimum
        and maximum like "m:n" or a concrete value / text.
      </li>
      <li>
        <strong>Status:</strong> <br /> You can select the shown status or the
        category of your visible results via the selection field.
      </li>
      <li>
        <strong>Sorting:</strong> <br /> You can sort the values of your rows by
        clicking on the column-header (asc and desc). Hold <code>shift</code>{" "}
        for multi-sorting
      </li>
      <li>
        <strong>Search:</strong> <br /> Search your task in the text field above
        the task-column.
      </li>
      <li>
        <strong>Link to source code:</strong> <br /> As before, click on the
        status / the task.
      </li>
    </ul>
    <h3> Quantile Plot and Scatter Plot</h3>
    <ul>
      <li>Select your values and additional lines</li>
      <li>Default settings are a logarithmic view with correct results only</li>
    </ul>
    <h3>Reset Filters</h3>
    <ul>
      <li>
        At any time you can reset all your the filters you have set in the table
      </li>
    </ul>
    <h3>Questions and Feedback </h3>
    <span>
      Fell free to write an e-Mail to{" "}
      <a
        className="link"
        href="mailto:wendler@sosy.ifi.lmu.de?subject=[HTMLResultTablegenerator]"
      >
        Dr. Philipp Wendler
      </a>
    </span>
    #{/* TODO: functional mail adress, e.g. tablegenerator@sosy.ifi.lmu.de */}
    <p>
      Generated by{" "}
      <a
        className="link"
        href="https://github.com/sosy-lab/benchexec"
        target="_blank"
        rel="noopener noreferrer"
      >
        {" "}
        BenchExec
      </a>
    </p>
    <details>
      <summary>
        This application includes third-party dependencies under different
        licenses. Click here to view them.
      </summary>
      {dependencies.dependencies.map(dependency => {
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
