// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import React, { useState, useEffect, useCallback, useMemo } from "react";
import {
  useTable,
  useFilters,
  useSortBy,
  usePagination,
  useResizeColumns,
  useFlexLayout,
} from "react-table";
import { useSticky } from "react-table-sticky";
import { useHistory } from "react-router-dom";
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
  isNil,
  hasSameEntries,
  setHashSearch,
  getHashSearch,
  getHiddenColIds,
} from "../utils/utils";
import deepEqual from "deep-equal";
import { statusForEmptyRows } from "../utils/filters";

const numericPattern = "([+-]?[0-9]*(\\.[0-9]*)?)(:[+-]?[0-9]*(\\.[0-9]*)?)?";

// Special markers we use as category for empty run results
const RUN_ABORTED = "aborted"; // result tag was present but empty (failure)
const RUN_EMPTY = "empty"; // result tag was not present in results XML
const SPECIAL_CATEGORIES = { [RUN_EMPTY]: "Empty rows", [RUN_ABORTED]: "—" };

const pageSizes = [50, 100, 250, 500, 1000, 2500];
const initialPageSize = 250;

const getSortingSettingsFromURL = () => {
  const urlParams = getHashSearch();
  let settings = urlParams.sort
    ? urlParams.sort.split(";").map((sortingEntry) => {
        const sortingParams = sortingEntry.split(",");
        const id = sortingParams[0];
        const desc = sortingParams[1] === "desc";
        return { id, desc };
      })
    : [];
  return settings;
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
    //if categoryFilters is a superset of categoryFilterValues, we know that all categories are selected
    out = categoryFilters;
  }
  if (!hasSameEntries(statusFilters, statusFilterValues)) {
    //if statusFilters is a superset of statusFilterValues, we know that all statuses are selected
    out = [...out, ...statusFilters];
  }

  return out;
};

const Table = (props) => {
  const [isFixed, setIsFixed] = useState(true);
  const [filteredColumnValues, setFilteredColumnValues] = useState({});
  const [columnsResizeValues, setColumnsResizeValues] = useState({});
  const [disableTaskText, setDisableTaskText] = useState(false);
  const history = useHistory();

  /**
   * This function automatically creates additional filters for status or category filters.
   * This is due to the fact that status and category filters are AND connected.
   * As only one status or category at a time can be selected in the Table view, this would
   * result in Filters like
   *      <Status X> AND <no categories>
   *  or
   *      <no status> AND <Category Y>
   *
   * which would always result in an empty result set.
   *
   */
  const createAdditionalFilters = ({ tool, name, column, isCategory }) => {
    const fill = isCategory ? props.statusValues : props.categoryValues;
    const out = [];

    for (const val of fill[tool][column]) {
      out.push({
        id: `${tool}_${name}_${column}`,
        value: `${val}${isCategory ? "" : " "}`,
      });
    }
    return out;
  };

  const selectAllStatusFields = ({ tool, name, column }) => {
    const out = [];

    for (const val of props.statusValues[tool][column]) {
      const value = val;
      out.push({
        id: `${tool}_${name}_${column}`,
        value,
      });
    }
    for (const val of props.categoryValues[tool][column]) {
      const value = `${val} `;
      out.push({
        id: `${tool}_${name}_${column}`,
        value, // categories are identified by the trailing space
      });
    }
    return out;
  };

  // Updates the filters that were set by React-Table in our backend
  const setCustomFilters = (newFilter) => {
    if (newFilter.id === "id") {
      newFilter.isTableTabFilter = true;
    }
    let filters = [
      ...props.filters.filter((propFilter) => propFilter.id !== newFilter.id),
      newFilter,
    ];
    // Filters with empty values represent filters that should be removed
    filters = filters.filter((filter) => filter.value !== "");
    props.addTypeToFilter(filters);

    let additionalFilters = [];

    if (newFilter.type === "status") {
      const [tool, name, column] = newFilter.id.split("_");
      const value = newFilter.value;

      if (value.trim() === "all") {
        additionalFilters = selectAllStatusFields({
          tool,
          name,
          column,
        });
        filters = filters.filter(
          ({ id, value }) => !(id === newFilter.id && value.trim() === "all"),
        );
      } else {
        const isCategory = value[value.length - 1] === " ";
        additionalFilters = createAdditionalFilters({
          tool,
          name,
          column,
          isCategory,
        });
      }
    }
    props.addTypeToFilter(additionalFilters);
    props.filterPlotData([...filters, ...additionalFilters], true);
  };

  // General filter input field
  function FilterInputField({ column: { id, filter }, currFilters }) {
    const elementId = id + "_filter";
    const setFilter = currFilters.find((filter) => filter.id === id);
    const initFilterValue = setFilter ? setFilter.value : "";
    let [typingTimer, setTypingTimer] = useState("");
    let [value, setValue] = useState(initFilterValue);

    const textPlaceholder =
      id === "id" && disableTaskText
        ? "To edit, please clear task filter in the sidebar"
        : "text";

    const onChange = (event) => {
      const newValue = event.target.value;
      setValue(newValue);
      clearTimeout(typingTimer);
      setTypingTimer(
        setTimeout(() => {
          setCustomFilters({ id, value: newValue });
          document.getElementById(elementId).focus();
        }, 500),
      );
    };

    return (
      <input
        id={elementId}
        className="filter-field"
        placeholder={textPlaceholder}
        defaultValue={value}
        onChange={onChange}
        disabled={id === "id" ? disableTaskText : false}
        type="search"
      />
    );
  }

  // Filter dropdown menu used for status columns
  function StatusFilter({ column: { id, filter }, runSetIdx, columnIdx }) {
    const categoryValues = props.categoryValues[runSetIdx][columnIdx];
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
      statusFilterValues: props.statusValues[runSetIdx][columnIdx],
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
        onChange={(event) =>
          setCustomFilters({ id, value: event.target.value })
        }
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
              <option value={category + " "} key={category}>
                {category}
              </option>
            ))}
        </optgroup>
        <optgroup label="Status">
          {props.statusValues[runSetIdx][columnIdx]
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

  // Filter input field used for columns with numerical values
  function MinMaxFilterInputField({ column: { id, filter }, currFilters }) {
    const elementId = id + "_filter";
    const setFilter = currFilters.find((filter) => filter.id === id);
    const initFilterValue = setFilter ? setFilter.value : "";
    let [typingTimer, setTypingTimer] = useState("");
    let [value, setValue] = useState(initFilterValue);

    const onChange = (event) => {
      const newValue = event.target.value;
      setValue(newValue);
      clearTimeout(typingTimer);
      setTypingTimer(
        setTimeout(() => {
          setCustomFilters({ id, value: newValue });
          document.getElementById(elementId).focus();
        }, 500),
      );
    };

    return (
      <input
        id={elementId}
        className="filter-field"
        placeholder="Min:Max"
        defaultValue={value}
        onChange={onChange}
        type="search"
        pattern={numericPattern}
      />
    );
  }

  const textFilterInputField = useCallback(
    (filterProps) => (
      <FilterInputField
        disableTaskText={disableTaskText}
        {...filterProps}
        currFilters={props.filters}
      />
    ),
    [disableTaskText, props.filters],
  );

  const minMaxFilterInputField = useCallback(
    (filterProps) => (
      <MinMaxFilterInputField {...filterProps} currFilters={props.filters} />
    ),
    [props.filters],
  );

  const columns = useMemo(() => {
    const createStatusColumn = (runSetIdx, column, columnIdx) => {
      const columnId = `${runSetIdx}_${column.display_title}_${columnIdx}`;
      const resizeWidth = columnsResizeValues[columnId];

      return {
        id: columnId,
        Header: <StandardColumnHeader column={column} />,
        className: "reg-column",
        hidden: props.hiddenCols[runSetIdx].includes(column.colIdx),
        minWidth: 50,
        width: resizeWidth || determineColumnWidth(column, 10),
        accessor: (row) => row.results[runSetIdx].values[columnIdx],
        Cell: (cell) => {
          const category = cell.row.original.results[runSetIdx].category;
          let href = cell.row.original.results[runSetIdx].href;
          let tooltip;
          if (category === "aborted") {
            href = undefined;
            tooltip = "Result missing because run was aborted or not executed";
          } else if (category === "empty") {
            tooltip =
              "Result missing because task was not part of benchmark set";
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
        sortType: (rowA, rowB, columnID, desc) =>
          textSortMethod(rowA.values[columnID], rowB.values[columnID]),
        // Don't let React-Table filter anything, we do it ourselves
        filter: (rows) => rows,
        Filter: (filter) => (
          <StatusFilter
            {...filter}
            runSetIdx={runSetIdx}
            columnIdx={columnIdx}
          />
        ),
      };
    };

    const createColumn = (runSetIdx, column, columnIdx) => {
      if (column.type === "status") {
        return createStatusColumn(runSetIdx, column, columnIdx);
      }

      const columnId = `${runSetIdx}_${column.display_title}_${columnIdx}`;
      const resizeWidth = columnsResizeValues[columnId];
      const filterType = isNumericColumn(column)
        ? minMaxFilterInputField
        : textFilterInputField;

      return {
        id: columnId,
        Header: <StandardColumnHeader column={column} />,
        className: "reg-column",
        hidden: props.hiddenCols[runSetIdx].includes(column.colIdx),
        minWidth: 50,
        width: resizeWidth || determineColumnWidth(column),
        accessor: (row) => row.results[runSetIdx].values[columnIdx],
        Cell: (cell) => (
          <StandardCell
            cell={cell}
            toggleLinkOverlay={props.toggleLinkOverlay}
          />
        ),
        // Don't let React-Table actually filter anything, we do it ourselves
        filter: (rows) => rows,
        Filter: filterType,
        sortType: (rowA, rowB, columnID, desc) =>
          isNumericColumn(column)
            ? numericSortMethod(rowA.values[columnID], rowB.values[columnID])
            : textSortMethod(rowA.values[columnID], rowB.values[columnID]),
      };
    };

    const createTaskIdColumn = () => ({
      Header: () => (
        <div className="fixed-task-header">
          <form>
            <label title="Fix the first column">
              Fixed task:
              <input
                name="fixed"
                type="checkbox"
                checked={isFixed}
                onChange={({ target }) => setIsFixed(target.checked)}
              />
            </label>
          </form>
        </div>
      ),
      className: "fixed-task",
      id: "task-id-column",
      sticky: isFixed ? "left" : "",
      columns: [
        {
          width: window.innerWidth * 0.3,
          minWidth: 230,
          ...(columnsResizeValues["id"] && {
            width: columnsResizeValues["id"],
          }),
          Header: (
            <StandardColumnHeader>
              <SelectColumnsButton handler={props.selectColumn} />
            </StandardColumnHeader>
          ),
          accessor: "id",
          Cell: (cell) => {
            const content = cell.row.original.id.map((id) => (
              <span key={id} className="row_id">
                {id}
              </span>
            ));
            const href = cell.row.original.href;
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
          Filter: textFilterInputField,
          sortType: (rowA, rowB, columnID, desc) => {
            const aValue = Array.isArray(rowA.values[columnID])
              ? rowA.values[columnID].join()
              : rowA.values[columnID];
            const bValue = Array.isArray(rowB.values[columnID])
              ? rowB.values[columnID].join()
              : rowB.values[columnID];
            return aValue > bValue ? 1 : aValue < bValue ? -1 : 0;
          },
        },
      ],
    });

    const resultColumns = props.tools
      .map((runSet, runSetIdx) =>
        createRunSetColumns(runSet, runSetIdx, createColumn),
      )
      .flat();

    return [createTaskIdColumn()].concat(resultColumns);
  }, [
    columnsResizeValues,
    isFixed,
    props,
    textFilterInputField,
    minMaxFilterInputField,
  ]);

  const data = useMemo(() => props.tableData, [props.tableData]);
  const defaultColumn = useMemo(
    () => ({
      Filter: <></>,
    }),
    [],
  );

  const {
    getTableProps,
    getTableBodyProps,
    headerGroups,
    rows,
    prepareRow,
    page,
    canPreviousPage,
    canNextPage,
    pageOptions,
    pageCount,
    gotoPage,
    nextPage,
    previousPage,
    setPageSize,
    setSortBy,
    state: { pageIndex, pageSize, sortBy, columnResizing },
  } = useTable(
    {
      columns,
      data,
      defaultColumn,
      initialState: {
        sortBy: getSortingSettingsFromURL(),
        pageIndex: parseInt(getHashSearch().page) - 1 || 0,
        hiddenColumns: getHiddenColIds(columns),
        pageSize: parseInt(getHashSearch().pageSize) || initialPageSize,
      },
    },
    useFilters,
    useFlexLayout,
    useResizeColumns,
    useSortBy,
    usePagination,
    useSticky,
  );

  // Update the URL sorting params when the table sorting settings changed
  useEffect(() => {
    const sort = sortBy
      .map(
        (sortingEntry) =>
          sortingEntry.id + "," + (sortingEntry.desc ? "desc" : "asc"),
      )
      .join(";");
    const value = sort.length ? sort : undefined;
    const prevParams = getHashSearch();
    if (prevParams["sort"] !== value) {
      setHashSearch({ sort: value }, { keepOthers: true });
    }
  }, [sortBy]);

  // Update the URL page size param when the table page size setting changed
  useEffect(() => {
    const value = pageSize !== initialPageSize ? pageSize : undefined;
    const prevParams = getHashSearch();
    if (prevParams["pageSize"] !== value) {
      setHashSearch({ pageSize: value }, { keepOthers: true });
    }
  }, [pageSize]);

  // Update the URL page param when the table page changed
  useEffect(() => {
    const value =
      pageIndex && pageIndex !== 0 ? Number(pageIndex) + 1 : undefined;
    const prevParams = getHashSearch();
    if (prevParams["page"] !== value) {
      setHashSearch({ page: value }, { keepOthers: true });
    }
  }, [pageIndex]);

  // Store the column resizing values so they can be applied again in case the table rerenders
  useEffect(() => {
    const widths = columnResizing.columnWidths;
    if (!columnResizing.isResizingColumn && Object.keys(widths).length > 0) {
      setColumnsResizeValues({ ...columnsResizeValues, ...widths });
    }
  }, [columnResizing, columnsResizeValues]);

  // get selected status and category values
  useEffect(() => {
    const newFilteredColumnValues = {};
    for (const filter of props.filters) {
      const { value, values, id } = filter;
      if (id === "id") {
        setDisableTaskText(!isNil(values));
      }
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
    if (!deepEqual(newFilteredColumnValues, filteredColumnValues)) {
      setFilteredColumnValues(newFilteredColumnValues);
    }
    // Set current page to new last page if current page is not legit any more after filtering
    if (pageIndex >= pageCount) {
      gotoPage(pageCount - 1);
    }
  }, [props.filters, filteredColumnValues, gotoPage, pageIndex, pageCount]);

  // Update table relevant parameters after URL change
  useEffect(() => {
    return history.listen((location) => {
      setPageSize(getHashSearch().pageSize || initialPageSize);
      setSortBy(getSortingSettingsFromURL());
      gotoPage(getHashSearch().page - 1 || 0);
    });
  }, [history, gotoPage, setPageSize, setSortBy]);

  const renderHeaderGroup = (headerGroup) => (
    <div className="tr headergroup" {...headerGroup.getHeaderGroupProps()}>
      {headerGroup.headers.map((header) => (
        <div
          {...header.getHeaderProps({
            className: `th header ${header.headers ? "outer " : ""}${
              header.className
            }`,
          })}
        >
          <div
            className={`header-sort-container ${
              header.isSorted
                ? header.isSortedDesc
                  ? "sorted-desc "
                  : "sorted-asc "
                : ""
            }`}
            {...header.getSortByToggleProps()}
          >
            {header.render("Header")}
          </div>
          {(!header.className || !header.className.includes("separator")) && (
            <div
              {...header.getResizerProps()}
              className={`resizer ${header.isResizing ? "isResizing" : ""}`}
            />
          )}
        </div>
      ))}
    </div>
  );

  const renderTableHeaders = (headerGroups) => {
    const runsetHeaderGroup = headerGroups[0];
    const headerGroupsWithFilters = headerGroups.filter((headerGroup) =>
      headerGroup.headers.some((header) => header.canFilter),
    );
    return (
      <div className="table-header">
        {renderHeaderGroup(runsetHeaderGroup)}
        <div className="shadow-container">
          {headerGroups.slice(1).map(renderHeaderGroup)}
          {headerGroupsWithFilters.map((headerGroup) => (
            <div
              className="tr headergroup filter"
              {...headerGroup.getHeaderGroupProps()}
            >
              {headerGroup.headers.map((header) => (
                <div
                  {...header.getHeaderProps({
                    className: `th header filter ${
                      header.headers ? "outer " : ""
                    }${header.className}`,
                  })}
                >
                  {header.canFilter ? header.render("Filter") : null}
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>
    );
  };

  const renderTableData = (rows) => (
    <div {...getTableBodyProps()} className="table-body body">
      {page.map((row) => {
        prepareRow(row);
        return (
          <div {...row.getRowProps()} className="tr">
            {row.cells.map((cell) => (
              <div
                {...cell.getCellProps({
                  className: "td " + (cell.column.className || ""),
                })}
              >
                {cell.render("Cell")}
              </div>
            ))}
          </div>
        );
      })}
    </div>
  );

  const renderPagination = () => (
    <div className="pagination">
      <div id="pagination-previous" className="pagination-container">
        <div
          onClick={() => previousPage()}
          className={`pagination-element button${
            !canPreviousPage ? " disabled" : ""
          }`}
        >
          Previous
        </div>{" "}
      </div>
      <div id="pagination-center" className="pagination-container">
        <div id="goto-page-element" className="pagination-element">
          Page
          <input
            aria-label="jump to page"
            type="number"
            value={Number(pageIndex) + 1}
            onChange={(e) => gotoPage(Number(e.target.value) - 1)}
          />
          of {pageOptions.length}
        </div>
        <div id="set-page-element" className="pagination-element">
          <select
            value={pageSize}
            onChange={(e) => setPageSize(Number(e.target.value))}
          >
            {pageSizes.map((pageSize) => (
              <option key={pageSize} value={pageSize}>
                {pageSize} rows
              </option>
            ))}
          </select>
        </div>
      </div>
      <div id="pagination-next" className="pagination-container">
        <div
          onClick={() => nextPage()}
          className={`pagination-element button${
            !canNextPage ? " disabled" : ""
          }`}
        >
          Next
        </div>{" "}
      </div>
    </div>
  );

  return (
    <div className="main-table">
      <div className="table sticky">
        <div className="table-content">
          <div className="table-container" {...getTableProps()}>
            {renderTableHeaders(headerGroups)}
            {renderTableData(rows)}
          </div>
        </div>
        {renderPagination()}
        <div className="-loading"></div>
      </div>
    </div>
  );
};

export default Table;
