// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import React from "react";

/**
  * Renders a setting (= a dropdown menu with its label) for one of the plots.
  *
  * @param {String} name name of the dropdown that will be used for the label next to it
  * @param {String} value default value that will be selected in the dropdown
  * @param {function} changeHandler handler function that will be called when an option was selected
  * @param {Object} options object containing the names of all options for the dropdown
  **/
const renderSetting = (name, value, changeHandler, options) => {
  return (
    <div className="setting">
      <span className="setting-label">{name}:</span>
      <select
        className="setting-select"
        name={name}
        value={value}
        onChange={changeHandler}
      >
        {Object.values(options).map((option) => (
          <option value={option} key={option} name={option + " " + name}>
            {option}
          </option>
        ))}
      </select>
    </div>
  );
};

export { renderSetting };
