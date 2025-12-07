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
      // @ts-expect-error TS(2339): Property 'className' does not exist on type 'Reado... Remove this comment to see the full error message
      className={this.props.className || "reset"}
      // @ts-expect-error TS(2339): Property 'onClick' does not exist on type 'Readonl... Remove this comment to see the full error message
      onClick={this.props.onClick}
      disabled={
        // @ts-expect-error TS(2339): Property 'enabled' does not exist on type 'Readonl... Remove this comment to see the full error message
        isNil(this.props.enabled) ? !this.props.isFiltered : !this.props.enabled
      }
    >
      <span>
        // @ts-expect-error TS(2339): Property 'filteredCount' does not exist on
        type 'R... Remove this comment to see the full error message Showing{" "}
        <span className="highlight">{this.props.filteredCount}</span> of{" "}
      </span>
      // @ts-expect-error TS(2339): Property 'className' does not exist on type
      'Reado... Remove this comment to see the full error message
      {(this.props.className || "").includes("tooltip") && (
        <span className="tooltiptext tooltip-bottom">Open filter menu</span>
      )}
      // @ts-expect-error TS(2339): Property 'totalCount' does not exist on type
      'Read... Remove this comment to see the full error message
      {this.props.totalCount} tasks // @ts-expect-error TS(2339): Property
      'className' does not exist on type 'Reado... Remove this comment to see
      the full error message
      {!(this.props.className || "").includes("header") && (
        <FontAwesomeIcon icon={faFilter} className="filter-icon" />
      )}
    </button>
  );
}
