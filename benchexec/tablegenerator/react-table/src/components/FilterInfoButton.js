// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import React from "react";
import { isNil } from "../utils/utils";
import { faFilter } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
export default class FilterInfoButton extends React.Component {
  render = () => (
    <button
      className={this.props.className || "reset"}
      onClick={this.props.onClick}
      disabled={
        isNil(this.props.enabled) ? !this.props.isFiltered : !this.props.enabled
      }
    >
      <span>
        Showing <span className="highlight">{this.props.filteredCount}</span> of{" "}
      </span>
      {(this.props.className || "").includes("tooltip") && (
        <span className="tooltiptext tooltip-bottom">Open filter menu</span>
      )}
      {this.props.totalCount} tasks
      {!(this.props.className || "").includes("header") && (
        <FontAwesomeIcon icon={faFilter} className="filter-icon" />
      )}
    </button>
  );
}
