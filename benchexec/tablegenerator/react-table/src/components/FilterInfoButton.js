// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import React from "react";
import { isNil } from "../utils/utils";
export default class FilterInfoButton extends React.Component {
  render = () => (
    <button
      className={this.props.className || "reset"}
      onClick={this.props.onClick || this.props.resetFilters}
      disabled={
        isNil(this.props.enabled) ? !this.props.isFiltered : !this.props.enabled
      }
    >
      <span className="hide">
        Showing <span className="highlight">{this.props.filteredCount}</span> of{" "}
      </span>
      {this.props.totalCount} tasks
      {this.props.showFilterText && (
        <span className="hide">
          {" "}
          (<span className="highlight">Reset Filters</span>)
        </span>
      )}
    </button>
  );
}
