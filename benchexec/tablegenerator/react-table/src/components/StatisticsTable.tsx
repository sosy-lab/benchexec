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

/* ============================================================================
 * Component props
 * ========================================================================== */

type StatisticsTableProps = {
  selectColumn: React.MouseEventHandler<HTMLSpanElement>;
  tools: ReadonlyArray<ToolLike>;
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
          tools: [...tools] as unknown as Parameters<
            typeof computeStats
          >[0]["tools"],
          tableData: [...tableData] as unknown as Parameters<
            typeof computeStats
          >[0]["tableData"],
          stats: [...defaultStats] as unknown as Parameters<
            typeof computeStats
          >[0]["stats"],
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
          {headerGroup.headers.map((header) => {
            // NOTE (JS->TS): react-table's v7 types don't include our custom `className`
            // and plugin-injected fields (e.g., `getResizerProps`, `isResizing`).
            // We narrow the header type locally to the fields we actually use.
            const h = header as HeaderGroup<StatRow> & {
              className?: string;
              columns?: unknown[];
              getResizerProps?: () => Record<string, unknown>;
              isResizing?: boolean;
            };

            return (
              <div
                {...h.getHeaderProps({
                  className: `th header ${h.columns ? "outer " : ""}${
                    h.className || ""
                  }`,
                })}
              >
                {h.render("Header")}

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

  const renderTableData = (
    rows: ReadonlyArray<Row<StatRow>>,
  ): React.ReactElement => (
    <div {...getTableBodyProps()} className="table-body body">
      {rows.map((row) => {
        prepareRow(row);
        return (
          <div {...row.getRowProps()} className="tr">
            {row.cells.map((cell) => {
              // NOTE (JS->TS): `className` is custom column metadata used for styling,
              // but react-table's types don't model it. We locally narrow the column type.
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
      ): {
        id: string;
        Header: React.JSX.Element;
        hidden: boolean;
        width: number;
        minWidth: number;
        accessor: (row: StatRow) => StatsCellValue | null | undefined;
        Cell: ({ value }: CellProps<StatRow, unknown>) => React.JSX.Element;
      } => ({
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
        Cell: ({ value }: CellProps<StatRow, unknown>) => {
          const typedValue = value as StatsCellValue | null | undefined;
          let valueToRender: unknown = typedValue?.sum;
          // We handle status differently as the main aggregation (denoted "sum")
          // is of type "count" for this column type.
          // This means that the default value if no data is available is 0
          if (column.type === "status") {
            if (typedValue === undefined) {
              // No data is available, default to 0
              valueToRender = 0;
            } else if (typedValue === null) {
              // We receive a null value directly from the stats object of the dataset.
              // Will be rendered as "-"
              // This edge case only applies to the summary-measurements row as it contains static values
              // that we can not calculate and therefore directly take them from the stats object.

              valueToRender = null;
            } else {
              const sum = typedValue.sum;
              valueToRender =
                Number.isInteger(Number(sum)) && sum !== undefined
                  ? Number(sum)
                  : sum;
            }
          }
          return !isNil(valueToRender) ? (
            <div
              dangerouslySetInnerHTML={{
                __html: valueToRender as unknown as string,
              }}
              className="cell"
              title={
                column.type !== "status" && typedValue
                  ? renderTooltip(typedValue)
                  : undefined
              }
            ></div>
          ) : (
            <div className="cell">-</div>
          );
        },
      });

    const createRowTitleColumn = (): {
      Header: () => React.JSX.Element;
      id: string;
      sticky: string;
      width: number;
      minWidth: number;
      columns: {
        id: string;
        width: number;
        minWidth: number;
        Header: React.JSX.Element;
        Cell: ({ row }: CellProps<StatRow>) => React.JSX.Element;
      }[];
    } => ({
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
          Cell: ({ row }: CellProps<StatRow>) => {
            // NOTE (JS->TS): Not all statistic rows are guaranteed to be listed in `statisticsRows`
            // (e.g., dataset-provided/static rows). We therefore look up the row definition
            // defensively and fall back to a reasonable default.
            const original = row.original as StatRow & {
              title?: string;
              description?: string;
            };

            const rowDefUnsafe = (statisticsRows as Record<string, unknown>)[
              original.id as unknown as string
            ] as
              | { title: string; indent?: number; description?: string }
              | undefined;

            const rowDef = rowDefUnsafe ?? { title: String(original.id) };
            const indent = "indent" in rowDef ? rowDef.indent ?? 0 : 0;
            const description =
              "description" in rowDef ? rowDef.description : undefined;

            return (
              <div
                dangerouslySetInnerHTML={{
                  __html:
                    (original.title ||
                      "&nbsp;".repeat(4 * indent) + rowDef.title) +
                    (filtered ? " of selected rows" : ""),
                }}
                title={original.description || description}
                className="row-title"
              />
            );
          },
        },
      ],
    });

    const statColumns = tools
      .map((runSet, runSetIdx) =>
        createRunSetColumns(
          runSet as unknown as Parameters<typeof createRunSetColumns>[0],
          runSetIdx,
          createColumnBuilder({
            switchToQuantile: switchToQuantile,
            hiddenCols,
          }) as unknown as Parameters<typeof createRunSetColumns>[2],
        ),
      )
      .flat();

    return [createRowTitleColumn(), ...(statColumns as Column<StatRow>[])];
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
