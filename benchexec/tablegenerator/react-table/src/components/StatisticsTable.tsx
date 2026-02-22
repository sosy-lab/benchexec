// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import React, { useState, useMemo, useEffect } from "react";

import {
  useTable,
  useFilters,
  useResizeColumns,
  useFlexLayout,
  type Column,
  type CellProps,
  type HeaderGroup,
  type Row,
  type TableInstance,
} from "react-table";
import { useSticky } from "react-table-sticky";
import {
  createRunSetColumns,
  SelectColumnsButton,
  StandardColumnHeader,
} from "./TableComponents";
import { computeStats, statisticsRows } from "../utils/stats";
import {
  determineColumnWidth,
  isNumericColumn,
  isNil,
  getHiddenColIds,
} from "../utils/utils";
import type { RowLike, ToolColumnLike, ToolLike } from "../types/reactTable";
import type { StatRow } from "../types/stats";

const isTestEnv = process.env.NODE_ENV === "test";

const titleColWidth = window.innerWidth * 0.15;

/* ============================================================================
 * Domain types
 * ========================================================================== */

type HiddenColsByRunSet = ReadonlyArray<ReadonlyArray<number>>;

/**
 * A single aggregated cell used in the statistics table (e.g., { sum: ..., avg: ..., max: ... }).
 * This matches what the statistics computation returns as "content" cells.
 */
type StatsCellValue = Record<string, unknown> & {
  sum?: unknown;
};

/**
 * Minimal runset/column shape used by this component.
 * We derive from ToolLike/ToolColumnLike, but enforce fields that this file relies on.
 */
type RunSetColumn = ToolColumnLike &
  Required<Pick<ToolColumnLike, "display_title">> & {
    colIdx: number;
    number_of_significant_digits: number;
  };

type RunSet = ToolLike &
  Required<Pick<ToolLike, "tool" | "date" | "niceName">> & {
    columns: ReadonlyArray<RunSetColumn>;
  };

/* ============================================================================
 * Component props
 * ========================================================================== */

type StatisticsTableProps = {
  selectColumn: React.MouseEventHandler<HTMLSpanElement>;
  tools: ReadonlyArray<RunSet>;
  switchToQuantile: (column: RunSetColumn) => void;
  hiddenCols: HiddenColsByRunSet;
  tableData: ReadonlyArray<RowLike>;
  onStatsReady?: () => void;
  stats: ReadonlyArray<StatRow>;
  filtered?: boolean;
};

const renderTooltip = (cell: StatsCellValue): string | undefined =>
  Object.keys(cell)
    .filter((key) => Boolean(cell[key]) && key !== "sum")
    .map((key) => `${key}: ${String(cell[key])}`)
    .join(", ") || undefined;

const StatisticsTable = ({
  selectColumn,
  tools,
  switchToQuantile,
  hiddenCols,
  tableData,
  onStatsReady,
  stats: defaultStats,
  filtered = false,
}: StatisticsTableProps): React.ReactElement => {
  // We want to skip stat calculation in a test environment if not
  // specifically wanted (signaled by a passed onStatsReady callback function)
  const skipStats = isTestEnv && !onStatsReady;

  // When filtered, initialize with empty statistics until computed statistics
  // are available in order to prevent briefly showing the wrong statistics.
  const [stats, setStats] = useState<ReadonlyArray<StatRow>>(
    filtered ? [] : defaultStats,
  );
  const [isTitleColSticky, setTitleColSticky] = useState(true);

  // we want to trigger a re-calculation of our stats whenever data changes.
  useEffect(() => {
    const updateStats = async (): Promise<void> => {
      if (filtered) {
        const newStats = await computeStats({
          tools,
          tableData,
          stats: defaultStats,
        });
        setStats(newStats);
      } else {
        setStats(defaultStats);
      }
      if (onStatsReady) {
        onStatsReady();
      }
    };
    if (!skipStats) {
      updateStats(); // necessary such that hook is not async
    }
  }, [tools, tableData, onStatsReady, skipStats, defaultStats, filtered]);

  const renderTableHeaders = (
    headerGroups: ReadonlyArray<HeaderGroup<StatRow>>,
  ): React.ReactElement => (
    <div className="table-header">
      {headerGroups.map((headerGroup) => (
        <div className="tr headergroup" {...headerGroup.getHeaderGroupProps()}>
          {headerGroup.headers.map((header) => (
            <div
              {...header.getHeaderProps({
                className: `th header ${header.headers ? "outer " : ""}${
                  header.className || ""
                }`,
              })}
            >
              {header.render("Header")}

              {(!header.className ||
                !header.className.includes("separator")) && (
                <div
                  {...header.getResizerProps()}
                  className={`resizer ${header.isResizing ? "isResizing" : ""}`}
                />
              )}
            </div>
          ))}
        </div>
      ))}
    </div>
  );

  const renderTableData = (
    rows: ReadonlyArray<Row<StatRow>>,
  ): React.ReactElement => (
    <div {...getTableBodyProps()} className="table-body body">
      {rows.map((row) => {
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

  const renderTable = (
    headerGroups: ReadonlyArray<HeaderGroup<StatRow>>,
    rows: ReadonlyArray<Row<StatRow>>,
  ): React.ReactElement => {
    if (filtered && stats.length === 0) {
      return (
        <p id="statistics-placeholder">
          Please wait while the statistics are being calculated.
        </p>
      );
    }
    return (
      <div id="statistics-table">
        <div className="table sticky">
          <div className="table-content">
            <div className="table-container" {...getTableProps()}>
              {renderTableHeaders(headerGroups)}
              {renderTableData(rows)}
            </div>
          </div>
        </div>
      </div>
    );
  };

  const columns = useMemo(() => {
    const createColumnBuilder =
      ({
        switchToQuantile: switchToQuantileInner,
        hiddenCols: hiddenColsInner,
      }: {
        switchToQuantile: (column: RunSetColumn) => void;
        hiddenCols: HiddenColsByRunSet;
      }) =>
      (
        runSetIdx: number,
        column: RunSetColumn,
        columnIdx: number,
      ): Column<StatRow> => ({
        id: `${runSetIdx}_${String(column.display_title)}_${columnIdx}`,
        Header: (
          <StandardColumnHeader
            column={column}
            className="header-data clickable"
            title="Show Quantile Plot of this column"
            onClick={() => switchToQuantileInner(column)}
          />
        ),
        hidden:
          Boolean(hiddenColsInner[runSetIdx]?.includes(column.colIdx)) ||
          !(isNumericColumn(column) || column.type === "status"),
        width: determineColumnWidth(
          column,
          undefined,
          column.type === "status" ? 6 : undefined,
        ),
        minWidth: 30,
        accessor: (row: StatRow): StatsCellValue | null | undefined => {
          const cell = row.content[runSetIdx]?.[columnIdx];
          if (
            cell === null ||
            cell === undefined ||
            typeof cell !== "object" ||
            Array.isArray(cell)
          ) {
            return cell as null | undefined;
          }
          return cell as StatsCellValue;
        },
        Cell: ({
          value,
          row,
        }: CellProps<StatRow, StatsCellValue | null | undefined>) => {
          let valueToRender: unknown = value?.sum;
          // We handle status differently as the main aggregation (denoted "sum")
          // is of type "count" for this column type.
          // This means that the default value if no data is available is 0
          if (column.type === "status") {
            if (value === undefined) {
              // No data is available, default to 0
              valueToRender = 0;
            } else if (value === null) {
              // We receive a null value directly from the stats object of the dataset.
              // Will be rendered as "-"
              // This edge case only applies to the summary-measurements row as it contains static values
              // that we can not calculate and therefore directly take them from the stats object.

              valueToRender = null;
            } else {
              const sum = value.sum;
              valueToRender =
                Number.isInteger(Number(sum)) && sum !== undefined
                  ? Number(sum)
                  : sum;
            }
          }
          return !isNil(valueToRender) ? (
            <div
              dangerouslySetInnerHTML={{
                __html: String(valueToRender),
              }}
              className="cell"
              title={
                column.type !== "status" && value
                  ? renderTooltip(value)
                  : undefined
              }
            ></div>
          ) : (
            <div className="cell">-</div>
          );
        },
      });

    const createRowTitleColumn = (): Column<StatRow> => ({
      Header: () => (
        <form>
          <label title="Fix the first column">
            Fixed row title:
            <input
              id="fixed-row-title"
              name="fixed"
              type="checkbox"
              checked={isTitleColSticky}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                setTitleColSticky(e.target.checked)
              }
            />
          </label>
        </form>
      ),
      id: "row-title",
      sticky: isTitleColSticky ? "left" : "",
      width: titleColWidth,
      minWidth: 100,
      columns: [
        {
          id: "summary",
          width: titleColWidth,
          minWidth: 100,
          Header: <SelectColumnsButton handler={selectColumn} />,
          Cell: ({ row }: CellProps<StatRow>) => (
            <div
              dangerouslySetInnerHTML={{
                __html:
                  ((row.original as StatRow).title ||
                    "&nbsp;".repeat(
                      4 *
                        (statisticsRows[(row.original as StatRow).id].indent ??
                          0),
                    ) + statisticsRows[(row.original as StatRow).id].title) +
                  (filtered ? " of selected rows" : ""),
              }}
              title={
                (row.original as StatRow).description ||
                statisticsRows[(row.original as StatRow).id].description
              }
              className="row-title"
            />
          ),
        },
      ],
    });

    const statColumns = tools
      .map((runSet, runSetIdx) =>
        createRunSetColumns(
          runSet,
          runSetIdx,
          createColumnBuilder({
            switchToQuantile: switchToQuantile,
            hiddenCols,
          }),
        ),
      )
      .flat();

    return [createRowTitleColumn()].concat(statColumns);
  }, [
    filtered,
    isTitleColSticky,
    switchToQuantile,
    hiddenCols,
    selectColumn,
    tools,
  ]);

  const data = useMemo(() => stats, [stats]);

  const { getTableProps, getTableBodyProps, headerGroups, rows, prepareRow } =
    useTable(
      {
        columns,
        data,
        initialState: {
          hiddenColumns: getHiddenColIds(columns),
        },
      },
      useFilters,
      useResizeColumns,
      useFlexLayout,
      useSticky,
    );

  return (
    <div id="statistics">
      <h2>Statistics</h2>
      {renderTable(headerGroups, rows)}
    </div>
  );
};

export default StatisticsTable;
