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
  type HeaderGroup,
  type Row,
} from "react-table";
import { useSticky } from "react-table-sticky";
import {
  createRunSetColumns,
  SelectColumnsButton,
  StandardColumnHeader,
} from "./TableComponents";
import type { TableColumnLike, ColumnTitleLike } from "./TableComponents";
import { computeStats, statisticsRows } from "../utils/stats";
import {
  determineColumnWidth,
  isNumericColumn,
  isNil,
  getHiddenColIds,
} from "../utils/utils";

const isTestEnv = process.env.NODE_ENV === "test";

const titleColWidth = window.innerWidth * 0.15;

/* ============================================================
 * Domain Types
 * ============================================================
 */

/**
 * The content of a stats cell as produced by computeStats() / dataset stats.
 * - For most numeric columns, we render `sum` as HTML.
 * - Additional keys can exist and are used for tooltips.
 */
type StatCellObject = {
  sum?: string | number | null;
  [key: string]: string | number | null | undefined;
};

type StatCellValue = StatCellObject | null | undefined;

/**
 * Minimal stat row shape used by StatisticsTable.
 * `title` and `description` are optional overrides used by the UI.
 */
export type StatRow = {
  id: keyof typeof statisticsRows;
  content: StatCellValue[][];
  title?: string;
  description?: string;
};

export type ToolColumn = {
  type?: string;
  title: string;
  number_of_significant_digits: number;

  // Used by StatisticsTable rendering/column building:
  display_title: React.ReactNode;
  colIdx: number;

  unit?: string;
  max_width?: number;
};

export type Tool = {
  tool: string;
  date: string;
  niceName: string;
  columns: ToolColumn[];
};

type TableRowResult = {
  category: string;
  values: Array<{ raw: string }>;
};

export type TableRow = {
  results: TableRowResult[];
};

/* ============================================================
 * Component Types
 * ============================================================
 */

export type StatisticsTableProps = {
  selectColumn: React.MouseEventHandler<HTMLSpanElement>;
  tools: Tool[];
  switchToQuantile: (col: ToolColumn) => void;
  hiddenCols: Array<number[] | undefined>;
  tableData: TableRow[];
  onStatsReady?: () => void;
  stats: StatRow[];
  filtered?: boolean;
};

const renderTooltip = (cell: StatCellObject): string | undefined =>
  Object.keys(cell)
    .filter((key) => cell[key] && key !== "sum")
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
  const [stats, setStats] = useState<StatRow[]>(filtered ? [] : defaultStats);
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
        setStats(newStats as StatRow[]);
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

  const renderTableHeaders = (headerGroups: Array<HeaderGroup<StatRow>>) => (
    <div className="table-header">
      {headerGroups.map((headerGroup) => (
        <div className="tr headergroup" {...headerGroup.getHeaderGroupProps()}>
          {headerGroup.headers.map((header) => {
            const h = header as HeaderGroup<StatRow> & {
              className?: string;
              columns?: unknown[];
              getResizerProps?: () => Record<string, unknown>;
              isResizing?: boolean;
            };

            return (
              <div
                {...h.getHeaderProps({
                  className: `th header ${header.headers ? "outer " : ""}${
                    h.className || ""
                  }`,
                })}
              >
                {header.render("Header")}

                {(!h.className || !h.className.includes("separator")) &&
                  h.getResizerProps && (
                    <div
                      {...h.getResizerProps()}
                      className={`resizer ${h.isResizing ? "isResizing" : ""}`}
                    />
                  )}
              </div>
            );
          })}
        </div>
      ))}
    </div>
  );

  const renderTableData = (rows: Array<Row<StatRow>>): React.ReactElement => (
    <div {...getTableBodyProps()} className="table-body body">
      {rows.map((row) => {
        prepareRow(row);
        return (
          <div {...row.getRowProps()} className="tr">
            {row.cells.map((cell) => {
              const column = cell.column as typeof cell.column & {
                className?: string;
              };

              return (
                <div
                  {...cell.getCellProps({
                    className: "td " + (column.className || ""),
                  })}
                >
                  {cell.render("Cell")}
                </div>
              );
            })}
          </div>
        );
      })}
    </div>
  );

  const renderTable = (
    headerGroups: Array<HeaderGroup<StatRow>>,
    rows: Array<Row<StatRow>>,
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

  const columns = useMemo((): Array<Column<StatRow>> => {
    const createColumnBuilder =
      ({
        switchToQuantile,
        hiddenCols,
      }: {
        switchToQuantile: StatisticsTableProps["switchToQuantile"];
        hiddenCols: StatisticsTableProps["hiddenCols"];
      }) =>
      (
        runSetIdx: number,
        column: ColumnTitleLike,
        columnIdx: number,
      ): TableColumnLike => {
        const hiddenForRunSet = hiddenCols[runSetIdx] ?? [];
        // TableComponents types `column` as ColumnTitleLike, but our dataset
        // provides a richer column object (incl. type/colIdx/etc.). We narrow via cast here.
        const fullColumn = column as ToolColumn;

        return {
          id: `${runSetIdx}_${String(fullColumn.display_title)}_${columnIdx}`,
          Header: (
            <StandardColumnHeader
              column={fullColumn}
              className="header-data clickable"
              title="Show Quantile Plot of this column"
              onClick={() => switchToQuantile(fullColumn)}
            />
          ),
          hidden:
            hiddenForRunSet.includes(fullColumn.colIdx) ||
            !(isNumericColumn(fullColumn) || fullColumn.type === "status"),
          width: determineColumnWidth(
            fullColumn,
            undefined,
            fullColumn.type === "status" ? 6 : undefined,
          ),
          minWidth: 30,
          accessor: (row: StatRow) => row.content[runSetIdx]?.[columnIdx],
          Cell: ({ value }: { value: StatCellValue }) => {
            let valueToRender: string | number | null | undefined =
              value && typeof value === "object" ? value.sum : undefined;

            // We handle status differently as the main aggregation (denoted "sum")
            // is of type "count" for this column type.
            // This means that the default value if no data is available is 0
            if (fullColumn.type === "status") {
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
                const maybeSum = value.sum;
                valueToRender = Number.isInteger(Number(maybeSum))
                  ? Number(maybeSum)
                  : maybeSum ?? null;
              }
            }

            return !isNil(valueToRender) ? (
              <div
                dangerouslySetInnerHTML={{
                  __html: valueToRender,
                }}
                className="cell"
                title={
                  fullColumn.type !== "status" &&
                  value &&
                  typeof value === "object"
                    ? renderTooltip(value)
                    : undefined
                }
              ></div>
            ) : (
              <div className="cell">-</div>
            );
          },
        } as unknown as TableColumnLike;
      };

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
              onChange={({ target }: React.ChangeEvent<HTMLInputElement>) =>
                setTitleColSticky(target.checked)
              }
            />
          </label>
        </form>
      ),
      id: "row-title",
      // NOTE (JS->TS):`sticky` is consumed by react-table-sticky at runtime
      // (react-table typings don't know it, but it's safe to keep as-is)
      // eslint-disable-next-line @typescript-eslint/ban-ts-comment
      // @ts-expect-error react-table-sticky runtime extension
      sticky: isTitleColSticky ? "left" : "",
      width: titleColWidth,
      minWidth: 100,
      columns: [
        {
          id: "summary",
          width: titleColWidth,
          minWidth: 100,
          Header: <SelectColumnsButton handler={selectColumn} />,
          Cell: ({ row }: { row: Row<StatRow> }) => (
            <div
              dangerouslySetInnerHTML={{
                __html:
                  (row.original.title ||
                    "&nbsp;".repeat(
                      4 *
                        ((
                          statisticsRows[row.original.id] as { indent?: number }
                        ).indent ?? 0),
                    ) + statisticsRows[row.original.id].title) +
                  (filtered ? " of selected rows" : ""),
              }}
              title={
                row.original.description ||
                (statisticsRows[row.original.id] as { description?: string })
                  .description
              }
              className="row-title"
            />
          ),
        } as Column<StatRow>,
      ],
    });

    const statColumns = tools
      .map((runSet, runSetIdx) =>
        createRunSetColumns(
          runSet,
          runSetIdx,
          createColumnBuilder({ switchToQuantile, hiddenCols }),
        ),
      )
      .flat() as Array<Column<StatRow>>;

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
    useTable<StatRow>(
      {
        columns,
        data,
        initialState: {
          hiddenColumns: getHiddenColIds(
            columns as unknown as Parameters<typeof getHiddenColIds>[0],
          ),
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
