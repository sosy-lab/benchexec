// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import React, { useState, useEffect } from "react";
import ReactTable from "react-table";
import "react-table/react-table.css";
import withFixedColumns from "react-table-hoc-fixed-columns";
import "react-table-hoc-fixed-columns/lib/styles.css";
import "react-table/react-table.css";
import {
  createRunSetColumns,
  StandardCell,
  StandardColumnHeader,
  SelectColumnsButton,
} from "./TableComponents.js";
import {
  isNumericColumn,
  numericSortMethod,
  textSortMethod,
  determineColumnWidth,
  pathOr,
  emptyStateValue,
} from "../utils/utils";

const numericPattern = "([+-]?[0-9]*(\\.[0-9]*)?)(:[+-]?[0-9]*(\\.[0-9]*)?)?";

function FilterInputField(props) {
  const elementId = props.column.id + "_filter";
  const filter = props.filter ? props.filter.value : props.filter;
  let value;
  let typingTimer;

  const onChange = (event) => {
    value = event.target.value;
    clearTimeout(typingTimer);
    typingTimer = setTimeout(() => {
      props.onChange(value);
      document.getElementById(elementId).focus();
    }, 500);
  };

  return (
    <input
      id={elementId}
      placeholder={props.numeric ? "Min:Max" : "text"}
      defaultValue={value ? value : filter}
      onChange={onChange}
      type="search"
      pattern={props.numeric ? numericPattern : undefined}
    />
  );
}

// Special markers we use as category for empty run results
const RUN_ABORTED = "aborted"; // result tag was present but empty (failure)
const RUN_EMPTY = "empty"; // result tag was not present in results XML
const SPECIAL_CATEGORIES = { [RUN_EMPTY]: "Empty rows", [RUN_ABORTED]: "—" };

const ReactTableFixedColumns = withFixedColumns(ReactTable);

export default function Table(props) {
  const [fixed, setFixed] = useState(true);
  let [filteredColumnValues, setFilteredColumnValues] = useState({});
  // get selected status and category values
  useEffect(() => {
    const { filtered } = props;
    const newFilteredColumnValues = {};
    for (const filter of filtered) {
      const { value, id } = filter;
      const [runset, , column] = id.split("_");
      const currentRunsetFilters = newFilteredColumnValues[runset] || {};

      const isCategory =
        typeof value === "string" && value[value.length - 1] === " ";

      if (isCategory) {
        const categories = currentRunsetFilters.categories || [];
        categories.push(value);
        currentRunsetFilters.categories = categories;
      } else {
        const filtersOfColumn = currentRunsetFilters[column] || [];
        filtersOfColumn.push(value);
        currentRunsetFilters[column] = filtersOfColumn;
      }

      newFilteredColumnValues[runset] = currentRunsetFilters;
    }
    setFilteredColumnValues(newFilteredColumnValues);

    console.log({ newFilteredColumnValues });
  }, [props]);

  const handleFixedInputChange = ({ target }) => {
    const value = target.checked;
    setFixed(value);
  };

  const createTaskIdColumn = () => ({
    Header: () => (
      <div className="fixed">
        <form>
          <label title="Fix the first column">
            Fixed task:
            <input
              name="fixed"
              type="checkbox"
              checked={fixed}
              onChange={handleFixedInputChange}
            />
          </label>
        </form>
      </div>
    ),
    fixed: fixed ? "left" : "",
    columns: [
      {
        minWidth: window.innerWidth * 0.3,
        Header: (
          <StandardColumnHeader>
            <SelectColumnsButton handler={props.selectColumn} />
          </StandardColumnHeader>
        ),
        fixed: fixed ? "left" : "",
        accessor: "id",
        Cell: (cell) => {
          const content = cell.value.map((id) => (
            <span key={id} className="row_id">
              {id}
            </span>
          ));
          const href = cell.original.href;
          return href ? (
            <a
              key={href}
              className="row__name--cellLink"
              href={href}
              title="Click here to show source code"
              onClick={(ev) => props.toggleLinkOverlay(ev, href)}
            >
              {content}
            </a>
          ) : (
            <span title="This task has no associated file">{content}</span>
          );
        },
        filterMethod: (filter, row) => {
          return true;
        },
        Filter: FilterInputField,
      },
    ],
  });

  const createStatusColumn = (runSetIdx, column, columnIdx) => ({
    id: `${runSetIdx}_${column.display_title}_${columnIdx}`,
    Header: <StandardColumnHeader column={column} />,
    show: column.isVisible,
    minWidth: determineColumnWidth(column, 10),
    accessor: (row) => row.results[runSetIdx].values[columnIdx],
    Cell: (cell) => {
      const category = cell.original.results[runSetIdx].category;
      let href = cell.original.results[runSetIdx].href;
      let tooltip;
      if (category === "aborted") {
        href = undefined;
        tooltip = "Result missing because run was aborted or not executed";
      } else if (category === "empty") {
        tooltip = "Result missing because task was not part of benchmark set";
      } else if (href) {
        tooltip = "Click here to show output of tool";
      }
      return (
        <StandardCell
          cell={cell}
          href={href}
          className={category}
          toggleLinkOverlay={props.toggleLinkOverlay}
          title={tooltip}
          force={true}
        />
      );
    },
    sortMethod: textSortMethod,
    filterMethod: (filter, row) => {
      return true;
    },
    Filter: ({ filter, onChange }) => {
      const categoryValues = props.categoryValues[runSetIdx][columnIdx];
      console.log({ filter });
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
      const selectedFilters = [
        ...selectedCategoryFilters,
        ...selectedStatusValues,
      ];
      const multipleSelected =
        selectedFilters.length > 1 || selectedFilters[0] === emptyStateValue;

      const singleFilterValue = filter ? filter.value : "all ";
      const selectValue = multipleSelected ? "multiple" : singleFilterValue;
      return (
        <select
          onChange={(event) => onChange(event.target.value)}
          style={{ width: "100%" }}
          value={selectValue}
        >
          {multipleSelected && (
            <option value="multiple" disabled selected>
              {selectedFilters
                .map((x) => x.trim())
                .filter((x) => x !== "all" && x !== emptyStateValue)
                .join(", ") || "Empty Set"}
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
              .map((category) => (
                // category filters are marked with space at end
                <option value={category + " "} key={category}>
                  {category}
                </option>
              ))}
          </optgroup>
          <optgroup label="Status">
            {props.statusValues[runSetIdx][columnIdx].map((status) => (
              <option value={status} key={status}>
                {status}
              </option>
            ))}
          </optgroup>
        </select>
      );
    },
  });

  const createColumn = (runSetIdx, column, columnIdx) => {
    if (column.type === "status") {
      return createStatusColumn(runSetIdx, column, columnIdx);
    }

    return {
      id: `${runSetIdx}_${column.display_title}_${columnIdx}`,
      Header: <StandardColumnHeader column={column} />,
      show: column.isVisible,
      minWidth: determineColumnWidth(column),
      accessor: (row) => row.results[runSetIdx].values[columnIdx],
      Cell: (cell) => (
        <StandardCell cell={cell} toggleLinkOverlay={props.toggleLinkOverlay} />
      ),
      filterMethod: () => true,
      Filter: (filter) => (
        <FilterInputField numeric={isNumericColumn(column)} {...filter} />
      ),
      sortMethod: isNumericColumn(column) ? numericSortMethod : textSortMethod,
    };
  };

  const resultColumns = props.tools
    .map((runSet, runSetIdx) =>
      createRunSetColumns(runSet, runSetIdx, createColumn),
    )
    .flat();

  console.log({ filtered: props.filtered });

  return (
    <div className="mainTable">
      <ReactTableFixedColumns
        data={props.data}
        filterable={true}
        filtered={props.filtered}
        columns={[createTaskIdColumn()].concat(resultColumns)}
        defaultPageSize={250}
        pageSizeOptions={[50, 100, 250, 500, 1000, 2500]}
        className="-highlight"
        minRows={0}
        onFilteredChange={(filtered) => {
          props.filterPlotData(filtered, true);
        }}
      >
        {(_, makeTable) => {
          return makeTable();
        }}
      </ReactTableFixedColumns>
    </div>
  );
}
