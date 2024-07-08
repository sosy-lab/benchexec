// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import { memo } from "react";
import { statusForEmptyRows } from "../../utils/filters";
import { pathOr, emptyStateValue, hasSameEntries } from "../../utils/utils";

// Special markers we use as category for empty run results
const RUN_ABORTED = "aborted"; // Result tag was present but empty (failure)
const RUN_EMPTY = "empty"; // Result tag was not present in results XML
const SPECIAL_CATEGORIES = {
  [RUN_EMPTY]: "Empty rows",
  [RUN_ABORTED]: "—",
};

/**
 * @typedef {Object} RelevantFilterParam
 * @property {string[]} categoryFilters - The category filters that are currently selected
 * @property {string[]} statusFilters - The status filters that are currently selected
 * @property {string[]} categoryFilterValues - All selectable category filter values
 * @property {string[]} statusFilterValues - All selectable status filter values
 */

/**
 * Function to extract the label of relevant filters to display.
 * If, for example, all category values are set and selected status values are "true" and "pass",
 * then only these status values will be displayed to the user as the category values have no
 * impact on filtering.
 *
 * @param {RelevantFilterParam} options
 * @returns {string[]} The labels to display to the user
 */
const createRelevantFilterLabel = ({
  categoryFilters,
  statusFilters,
  categoryFilterValues,
  statusFilterValues,
}) => {
  let out = [];

  if (!hasSameEntries(categoryFilters, categoryFilterValues)) {
    // If categoryFilters is a superset of categoryFilterValues,
    // we know that all categories are selected
    out = categoryFilters;
  }
  if (!hasSameEntries(statusFilters, statusFilterValues)) {
    // If statusFilters is a superset of statusFilterValues,
    // we know that all statuses are selected
    out = [...out, ...statusFilters];
  }

  return out;
};

/**
 * Component to display a filter dropdown for the status column.
 * A memoized version of the component is default exported.
 */
function StatusFilter({
  column: { id },
  runSetIdx,
  columnIdx,
  allCategoryValues,
  allStatusValues,
  filteredColumnValues,
  setCustomFilters,
}) {
  const categoryValues = allCategoryValues[runSetIdx][columnIdx];
  const selectedCategoryFilters = pathOr(
    [runSetIdx, "categories"],
    [],
    filteredColumnValues,
  );
  const selectedStatusValues = pathOr(
    [runSetIdx, columnIdx],
    [],
    filteredColumnValues,
  );

  const selectedFilters = createRelevantFilterLabel({
    categoryFilters: selectedCategoryFilters,
    statusFilters: selectedStatusValues,
    categoryFilterValues: categoryValues.map((item) => `${item} `),
    statusFilterValues: allStatusValues[runSetIdx][columnIdx],
  });

  const allSelected = selectedFilters.length === 0;
  const multipleSelected =
    selectedFilters.length > 1 || selectedFilters[0] === emptyStateValue;
  const singleFilterValue = selectedFilters && selectedFilters[0];
  const selectValue =
    (allSelected && "all ") ||
    (multipleSelected && "multiple") ||
    singleFilterValue;

  return (
    <select
      className="filter-field"
      onChange={(event) => setCustomFilters({ id, value: event.target.value })}
      value={selectValue}
    >
      {multipleSelected && (
        <option value="multiple" disabled>
          {selectedFilters
            .map((x) => x.trim())
            .filter((x) => x !== "all" && x !== emptyStateValue)
            .join(", ") || "No filters selected"}
        </option>
      )}
      <option value="all ">Show all</option>
      {categoryValues
        .filter((category) => category in SPECIAL_CATEGORIES)
        .map((category) => (
          // category filters are marked with space at end
          <option value={category + " "} key={category}>
            {SPECIAL_CATEGORIES[category]}
          </option>
        ))}
      <optgroup label="Category">
        {categoryValues
          .filter((category) => !(category in SPECIAL_CATEGORIES))
          .sort()
          .map((category) => (
            // category filters are marked with space at end
            <option value={category + " "} key={category} className={category}>
              {category}
            </option>
          ))}
      </optgroup>
      <optgroup label="Status">
        {allStatusValues[runSetIdx][columnIdx]
          .filter((status) => status !== statusForEmptyRows)
          .sort()
          .map((status) => (
            <option value={status} key={status}>
              {status}
            </option>
          ))}
      </optgroup>
    </select>
  );
}

export default memo(StatusFilter);
