/* SPDX-License-Identifier: Apache-2.0
 *
 * BenchExec is a framework for reliable benchmarking.
 * This file is part of BenchExec.
 * Copyright (C) Dirk Beyer. All rights reserved.
 */
import React from "react";
import { formatColumnTitle, getRunSetName } from "../utils/utils.js";

export const SelectColumnsButton = ({ handler, ...other }) => (
  <span onClick={handler} className="selectColumns" {...other}>
    Click here to select columns
  </span>
);

export const StandardColumnHeader = ({
  column,
  title = "Click here to sort. Hold shift to multi-sort",
  ...other
}) => (
  <div title={title} {...other}>
    {formatColumnTitle(column)}
  </div>
);

export const RunSetHeader = ({ runSet, ...other }) => (
  <span className="header__tool-infos" {...other}>
    {getRunSetName(runSet)}
  </span>
);
