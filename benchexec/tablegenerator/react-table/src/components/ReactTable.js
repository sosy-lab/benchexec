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
import { useLocation } from "react-router-dom";
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
  isNil,
  setURLParameter,
  getURLParameters,
  getHiddenColIds,
  decodeFilter,
} from "../utils/utils";
import deepEqual from "deep-equal";
import {
  StatusFilter,
  MinMaxFilterInputField,
  FilterInputField,
} from "./Table";

const pageSizes = [50, 100, 250, 500, 1000, 2500];
const initialPageSize = 250;

const getSortingSettingsFromURL = () => {
  const urlParams = getURLParameters();
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

const Table = (props) => {
  const [isFixed, setIsFixed] = useState(true);
  const [filteredColumnValues, setFilteredColumnValues] = useState(
    getNewFilteredColumnValues(),
  );
  const [columnsResizeValues, setColumnsResizeValues] = useState({});
  const [disableTaskText, setDisableTaskText] = useState(false);
  const [focusedFilter, setFocusedFilter] = useState(null);

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
  const createAdditionalFilters = useCallback(
    ({ tool, name, column, isCategory }) => {
      const fill = isCategory ? props.statusValues : props.categoryValues;
      const out = [];

      for (const val of fill[tool][column]) {
        out.push({
          id: `${tool}_${name}_${column}`,
          value: `${val}${isCategory ? "" : " "}`,
        });
      }
      return out;
    },
    [props.categoryValues, props.statusValues],
  );

  const selectAllStatusFields = useCallback(
    ({ tool, name, column }) => {
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
    },
    [props.categoryValues, props.statusValues],
  );

  // Updates the filters that were set by React-Table in our backend
  const setCustomFilters = useCallback(
    (newFilter) => {
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
        const { tool, name, column } = decodeFilter(newFilter.id);
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
    },
    [props, createAdditionalFilters, selectAllStatusFields],
  );

  const textFilterInputField = useCallback(
    (filterProps) => {
      const id = filterProps.column.id;
      const setFilter = props.filters.find((filter) => filter.id === id);

      return (
        <FilterInputField
          id={id}
          setFilter={setFilter}
          disableTaskText={disableTaskText}
          setCustomFilters={setCustomFilters}
          focusedFilter={focusedFilter}
          setFocusedFilter={setFocusedFilter}
        />
      );
    },
    [disableTaskText, props.filters, setCustomFilters, focusedFilter],
  );

  const minMaxFilterInputField = useCallback(
    (filterProps) => {
      const id = filterProps.column.id;
      const setFilter = props.filters.find((filter) => filter.id === id);
      return (
        <MinMaxFilterInputField
          id={id}
          setFilter={setFilter}
          setCustomFilters={setCustomFilters}
          focusedFilter={focusedFilter}
          setFocusedFilter={setFocusedFilter}
        />
      );
    },
    [props.filters, setCustomFilters, focusedFilter],
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
        sortType: (rowA, rowB, columnID, _desc) =>
          textSortMethod(rowA.values[columnID], rowB.values[columnID]),
        // Don't let React-Table filter anything, we do it ourselves
        filter: (rows) => rows,
        Filter: (filter) => (
          <StatusFilter
            {...filter}
            runSetIdx={runSetIdx}
            columnIdx={columnIdx}
            allCategoryValues={props.categoryValues}
            allStatusValues={props.statusValues}
            filteredColumnValues={filteredColumnValues}
            setCustomFilters={setCustomFilters}
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
        sortType: (rowA, rowB, columnID, _desc) =>
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
          sortType: (rowA, rowB, columnID, _desc) => {
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
    filteredColumnValues,
    setCustomFilters,
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
        pageIndex: parseInt(getURLParameters().page) - 1 || 0,
        hiddenColumns: getHiddenColIds(columns),
        pageSize: parseInt(getURLParameters().pageSize) || initialPageSize,
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
    setURLParameter({ sort: value });
  }, [sortBy]);

  // Update the URL page size param when the table page size setting changed
  useEffect(() => {
    const value = pageSize !== initialPageSize ? pageSize : undefined;
    setURLParameter({ pageSize: value });
  }, [pageSize]);

  // Update the URL page param when the table page changed
  useEffect(() => {
    const value =
      pageIndex && pageIndex !== 0 ? Number(pageIndex) + 1 : undefined;
    setURLParameter({ page: value });
  }, [pageIndex]);

  // Store the column resizing values so they can be applied again in case the table rerenders
  useEffect(() => {
    const widths = columnResizing.columnWidths;
    if (!columnResizing.isResizingColumn && Object.keys(widths).length > 0) {
      setColumnsResizeValues({ ...columnsResizeValues, ...widths });
    }
  }, [columnResizing, columnsResizeValues]);

  // Convert the props.filters array into Filtered Column Values object
  function getNewFilteredColumnValues() {
    const newFilteredColumnValues = {};
    for (const filter of props.filters) {
      const { value, id } = filter;
      const { tool: runset, column } = decodeFilter(id);
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
    return newFilteredColumnValues;
  }

  // get selected status and category values
  useEffect(() => {
    // To disable task text if any task filter is applied
    setDisableTaskText(
      props.filters.some(({ id, values }) => id === "id" && !isNil(values)),
    );

    let newFilteredColumnValues = getNewFilteredColumnValues();
    if (!deepEqual(newFilteredColumnValues, filteredColumnValues)) {
      setFilteredColumnValues(newFilteredColumnValues);
    }
    // Set current page to new last page if current page is not legit any more after filtering
    if (pageIndex >= pageCount) {
      gotoPage(pageCount - 1);
    }

    // react-hooks/exhaustive-deps shows that getNewFilteredColumnValues to be included in the dependency array.
    // But useEffect functionality is not dependent on getNewFilteredColumnValues as it never changes.
    // So react-hooks/exhaustive-deps can be ignored here.

    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [props.filters, filteredColumnValues, gotoPage, pageIndex, pageCount]);

  // Update table relevant parameters after URL change
  const location = useLocation();
  useEffect(
    (_location) => {
      setPageSize(getURLParameters().pageSize || initialPageSize);
      setSortBy(getSortingSettingsFromURL());
      gotoPage(getURLParameters().page - 1 || 0);
    },
    // We have also added window.location.href to the dependency array to ensure that
    // the table is updated when the URL changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [location, setPageSize, setSortBy, gotoPage, window.location.href],
  );

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
            {...(header.canSort &&
              (!header.className || !header.className.includes("separator")) &&
              header.getSortByToggleProps({
                className: `header-sort-container clickable ${
                  header.isSorted
                    ? header.isSortedDesc
                      ? "sorted-desc "
                      : "sorted-asc "
                    : ""
                }`,
              }))}
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
      </div>
    </div>
  );
};

export default Table;
