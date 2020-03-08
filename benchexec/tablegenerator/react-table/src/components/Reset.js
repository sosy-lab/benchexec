/* SPDX-License-Identifier: Apache-2.0
 *
 * BenchExec is a framework for reliable benchmarking.
 * This file is part of BenchExec.
 * Copyright (C) Dirk Beyer. All rights reserved.
 */
import React from "react";

export default class Reset extends React.Component {
  render = () => (
    <button
      className="reset"
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
