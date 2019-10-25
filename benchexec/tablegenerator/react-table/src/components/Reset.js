/* SPDX-License-Identifier: Apache-2.0
 *
 * BenchExec is a framework for reliable benchmarking.
 * This file is part of BenchExec.
 * Copyright (C) Dirk Beyer. All rights reserved.
 */
import React from "react";
export default class Reset extends React.Component {
  render() {
    return this.props.isFiltered ? (
      <button className="reset" onClick={this.props.resetFilters}>
        Reset Filters
      </button>
    ) : null;
  }
}
