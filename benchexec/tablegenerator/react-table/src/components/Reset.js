// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import React from "react";
export default class Reset extends React.Component {
  render = () => (
    <button
      className={this.props.className || "reset"}
      onClick={this.props.resetFilters}
      disabled={!this.props.isFiltered}
    >
      <span className="hide">
        Showing <span className="highlight">{this.props.filteredCount}</span> of{" "}
      </span>
      {this.props.totalCount} tasks
      <span className="hide">
        {" "}
        (<span className="highlight">Reset Filters</span>)
      </span>
    </button>
  );
}
