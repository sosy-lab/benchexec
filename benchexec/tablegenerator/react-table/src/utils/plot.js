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
      <span className={`setting-label${tooltip ? " with-tooltip" : ""}`}>
        {name}:
      </span>
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
      <span className={`setting-label${tooltip ? " with-tooltip" : ""}`}>
        {name}:
      </span>
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

/**
 * Returns an object containing arrays of data points (of the format [x-value, y-value]) that represent the upper and lower
 * borders of the 95% confidence interval of the linear regression line. Calculation is done via the formula provided by
 * https://www2.stat.duke.edu/courses/Spring13/sta101.001/slides/unit6lec3H.pdf
 * @param {Array} actualData array of actual data points that were used for the linear regression
 * @param {Array} predictedData array of calculated data points that represent the linear regression line
 * @param {function} regressionFunction function that calculates the predicted values
 * @param {int} minX leftmost x value for the borders
 * @param {int} maxX rightmost x value for the borders
 */
function getConfidenceIntervalBorders(
  actualData,
  predictedData,
  regressionFunction,
  minX,
  maxX,
) {
  const getXValue = (data) => data[0];
  const getYValue = (data) => data[1];
  const sum = (x, y) => x + y;
  minX = Math.floor(minX);
  maxX = Math.ceil(maxX);
  // Value of the t-statistic for a 95% confidence interval
  const tValue = 1.96;
  const stdErr = Math.sqrt(
    actualData
      .map((data, index) => [getYValue(data), getYValue(predictedData[index])])
      .map((yValues) => Math.pow(yValues[1] - yValues[0], 2))
      .reduce(sum) / actualData.length,
  );
  const meanOfX =
    actualData.map((data) => getXValue(data)).reduce(sum) / actualData.length;
  const stdOfX = Math.sqrt(
    actualData
      .map((data) => Math.pow(getXValue(data) - meanOfX, 2))
      .reduce(sum) / actualData.length,
  );

  const dataPointsOfRegression = getDataPointsOfRegression(
    minX,
    maxX,
    regressionFunction,
  );

  const diffMargins = dataPointsOfRegression.map(
    (data) =>
      tValue *
      stdErr *
      Math.sqrt(
        1 / actualData.length +
          Math.pow(getXValue(data) - meanOfX, 2) /
            ((actualData.length - 1) * Math.pow(stdOfX, 2)),
      ),
  );

  return {
    upperBorderData: dataPointsOfRegression.map((data, index) => [
      getXValue(data),
      getYValue(data) + diffMargins[index],
    ]),
    lowerBorderData: dataPointsOfRegression.map((data, index) => [
      getXValue(data),
      getYValue(data) - diffMargins[index],
    ]),
  };
}
/* Computes the data points that will be plotted for a regression. The maximum
   number of data points will not exceed 10.000. If there were more, the lines
   will be plotted in intervals. */
function getDataPointsOfRegression(minX, maxX, regF) {
  const thresholds = [100000000, 10000000, 1000000, 100000, 10000];
  const threshold = thresholds.find((threshold) => maxX > threshold);
  const numberPointsDivider = threshold ? threshold / 1000 : 1;
  const dataPointsOfRegression = Array(Math.ceil(maxX / numberPointsDivider))
    .fill()
    .map((x, index) => index * numberPointsDivider);

  return dataPointsOfRegression
    .filter((int) => int >= minX)
    .map((number) => {
      const pred = regF(number);
      return [
        Number.parseFloat(pred[0].toPrecision(4)),
        Number.parseFloat(pred[1].toPrecision(4)),
      ];
    });
}

export {
  renderSetting,
  renderOptgroupsSetting,
  getConfidenceIntervalBorders,
  getDataPointsOfRegression,
};
