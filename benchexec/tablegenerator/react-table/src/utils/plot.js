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
 * @param {String} tooltip [OPTIONAL] tooltip for the whole setting
 * @param {boolean} isDisabled [OPTIONAL] whether or not the dropdown is disabled
 **/
const renderSetting = (
  name,
  value,
  changeHandler,
  options,
  tooltip,
  isDisabled,
) => {
  return (
    <div className={`setting${isDisabled ? " disabled" : ""}`} title={tooltip}>
      <span className="setting-label">{name}:</span>
      <select
        className="setting-select"
        name={"setting-" + name}
        value={isDisabled ? "disabled" : value}
        onChange={changeHandler}
        disabled={isDisabled}
      >
        {Object.values(options).map((option) => (
          <option value={option} key={option} name={option + " " + name}>
            {option}
          </option>
        ))}
        {isDisabled ? (
          <option value="disabled" name="disabled">
            ⸺
          </option>
        ) : (
          ""
        )}
      </select>
    </div>
  );
};

/**
 * Renders a setting (= a dropdown menu with its label) for one of the plots.
 *
 * @param {String} name name of the dropdown that will be used for the label next to it
 * @param {String} value default value that will be selected in the dropdown
 * @param {function} changeHandler handler function that will be called when an option was selected
 * @param {Object} options object containing the name of the optgroup as key and an array of objects representing the selections
   with their display name and their value property
 * @param {String} tooltip [OPTIONAL] tooltip for the whole setting
 **/
const renderOptgroupsSetting = (
  name,
  value,
  changeHandler,
  options,
  tooltip,
) => {
  return (
    <div className="setting" title={tooltip}>
      <span className="setting-label">{name}:</span>
      <select
        id={"setting-" + name}
        className="setting-select"
        name={"setting-" + name}
        value={value}
        onChange={changeHandler}
      >
        {Object.entries(options).map(([optgroup, selections]) => (
          <optgroup label={optgroup} key={optgroup}>
            {selections.map((optionObj) => (
              <option
                value={optionObj.value}
                key={optionObj.value}
                name={optionObj.name + " " + name}
              >
                {optionObj.name}
              </option>
            ))}
          </optgroup>
        ))}
      </select>
    </div>
  );
};

export { renderSetting, renderOptgroupsSetting };
