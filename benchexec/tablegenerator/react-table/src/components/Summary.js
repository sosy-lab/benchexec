// This file is part of BenchExec, a framework for reliable benchmarking:
// https://github.com/sosy-lab/benchexec
//
// SPDX-FileCopyrightText: 2019-2020 Dirk Beyer <https://www.sosy-lab.org>
//
// SPDX-License-Identifier: Apache-2.0

import React, { useMemo, useState, useEffect } from "react";
import { useFlexLayout, useResizeColumns, useTable } from "react-table";
import { statisticsRows, computeStats } from "../utils/stats";
import { SelectColumnsButton } from "./TableComponents";
import StatisticsTable from "./StatisticsTable";

const infos = [
  "displayName",
  "tool",
  "limit",
  "host",
  "os",
  "system",
  "date",
  "runset",
  "branch",
  "options",
  "property",
];

const isTestEnv = process.env.NODE_ENV === "test";

// Renders the options of a tool in a list
const Options = ({ text }) => {
  if (!text) {
    return null;
  }

  return (
    <ul style={{ listStyleType: "none" }}>
      {text.split(/[\s]+-/).map((option, i) => (
        <li key={option} style={{ textAlign: "left", fontSize: "9pt" }}>
          <code>{i === 0 ? option : `-${option}`}</code>
        </li>
      ))}
    </ul>
  );
};

// Renders a link to a tool and its version
const ExternalLink = ({ url, text }) => {
  if (url) {
    return (
      <a href={url} target="_blank" rel="noopener noreferrer">
        {text}
      </a>
    );
  }

  return <>{text}</>;
};

// Renders the name of a tool and its version
const ToolNameAndVersion = ({ tool, version, project_url, version_url }) => {
  return (
    <>
      <ExternalLink url={project_url} text={tool} />{" "}
      <ExternalLink url={version_url} text={version} />
    </>
  );
};

const Summary = ({
  tools,
  tableHeader,
  version,
  selectColumn,
  stats: defaultStats,
  onStatsReady,
  switchToQuantile,
  tableData,
  hiddenCols,
  filtered,
}) => {
  // We want to skip stat calculation in a test environment if not
  // specifically wanted (signaled by a passed onStatsReady callback function)
  const skipStats = isTestEnv && !onStatsReady;

  const [isTitleColSticky, setTitleColSticky] = useState(true);

  // When filtered, initialize with empty statistics until computed statistics
  // are available in order to prevent briefly showing the wrong statistics.
  const [stats, setStats] = useState(filtered ? [] : defaultStats);

  // We want to trigger a re-calculation of our stats whenever data changes.
  useEffect(() => {
    const updateStats = async () => {
      if (filtered) {
        const newStats = await computeStats({
          tools,
          tableData,
          stats: defaultStats,
        });
        setStats(newStats);
      } else {
        setStats(stats);
      }
      if (onStatsReady) {
        onStatsReady();
      }
    };

    if (!skipStats) {
      // This is necessary as the hook is not async
      updateStats();
    }
  }, [
    tools,
    tableData,
    onStatsReady,
    skipStats,
    stats,
    filtered,
    defaultStats,
  ]);

  const BenchmarkCols = useMemo(() => {
    let colArray = [];

    infos.forEach((row) => {
      let tableHeaderRow = tableHeader[row];
      if (tableHeaderRow) {
        colArray.push({
          accessor: tableHeaderRow.id,
          Header: tableHeaderRow.name,
          sticky: "left",
        });
      }
    });

    colArray.push({
      Header: (
        <SelectColumnsButton
          handler={selectColumn}
          style={{
            border: "1px solid #DDD",
            borderRadius: "5px",
            width: "100%",
            padding: "2px",
          }}
        />
      ),
      id: "columnselect",
      accessor: "columnselect",
      statisticTable: true,
    });

    for (const stat in stats) {
      if (stats[stat].title) {
        colArray.push({
          Header: stats[stat].title,
          stats: true,
        });
      } else {
        colArray.push({
          Header:
            "\xa0".repeat(4 * statisticsRows[stats[stat].id].indent) +
            statisticsRows[stats[stat].id].title +
            (filtered ? " of selected rows" : ""),
          stats: true,
          minWidth: 300,
        });
      }
    }

    return colArray;
  }, [tableHeader, stats, selectColumn, filtered]);

  const BenchmarkData = useMemo(() => {
    let dataArray = [];

    tools.forEach((runSet, runSetIndex) => {
      dataArray.push({
        colspan: {
          columnselect: tableHeader.tool.content[runSetIndex][1],
        },
        columnselect: {
          runSet,
          runSetIndex: runSetIndex,
          runSetStats: stats,
        },
      });
    });

    infos.forEach((row) => {
      let tableHeaderRow = tableHeader[row];
      if (tableHeaderRow) {
        tableHeaderRow.content.forEach((cont, index) => {
          let dataElement = dataArray[index];
          dataArray[index] = {
            ...dataElement,
            [tableHeaderRow.id]: cont[0],
            colspan: { ...dataElement.colspan, [tableHeaderRow.id]: cont[1] },
          };
        });
      }
    });

    return dataArray;
  }, [tableHeader, tools, stats]);

  const { getTableProps, getTableBodyProps, headers, rows, prepareRow } =
    useTable(
      { columns: BenchmarkCols, data: BenchmarkData },
      useFlexLayout,
      useResizeColumns,
    );

  return (
    <div id="summary">
      <h2>Benchmark Setup</h2>

      <div id="benchmark_setup">
        <form id="stickyform">
          <label title="Fix the first column" htmlFor="fixed-row-title">
            Fixed row title:
          </label>
          <input
            id="fixed-row-title"
            name="fixed"
            type="checkbox"
            style={{ width: 20, height: 20 }}
            checked={isTitleColSticky}
            onChange={({ target }) => setTitleColSticky(target.checked)}
          />
        </form>

        <table {...getTableProps()} style={{ border: "1px solid black" }}>
          <tbody {...getTableBodyProps()}>
            {headers.map((col, index) => {
              return (
                <tr key={index}>
                  <th
                    className={`${isTitleColSticky && "sticky"}`}
                    {...col.getHeaderProps()}
                  >
                    {col.render("Header")}
                  </th>

                  {/* Resizer */}
                  <td
                    {...col.getResizerProps()}
                    style={{
                      margin: "0px",
                      padding: "0px",
                      cursor: "col-resize",
                      background: "rgba(0, 0, 0, 0.1)",
                    }}
                  />

                  {!col.stats &&
                    rows.map((row, index) => {
                      prepareRow(row);

                      if (row.values[col.id] === undefined) {
                        return null;
                      }

                      return (
                        <td
                          key={index}
                          colSpan={
                            (row.original.colspan &&
                              row.original.colspan[col.id]) ||
                            1
                          }
                          rowSpan={col.id === "columnselect" ? infos.length : 1}
                          {...row.cells[index].getCellProps()}
                          style={{
                            padding: col.id === "columnselect" && 0,
                            margin: 0,
                          }}
                        >
                          {col.id === "columnselect" ? (
                            <StatisticsTable
                              key={index}
                              tableData={row.values[col.id]}
                              switchToQuantile={switchToQuantile}
                              hiddenCols={hiddenCols}
                            />
                          ) : col.id === "options" ? (
                            <ul style={{ margin: 0, paddingLeft: 17 }}>
                              <Options text={row.values[col.id]} />
                            </ul>
                          ) : col.id === "tool" ? (
                            <ToolNameAndVersion {...row.values[col.id]} />
                          ) : (
                            row.values[col.id]
                          )}
                        </td>
                      );
                    })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <p>
        Generated by{" "}
        <a
          className="link"
          href="https://github.com/sosy-lab/benchexec"
          target="_blank"
          rel="noopener noreferrer"
        >
          BenchExec {version}
        </a>
      </p>
    </div>
  );
};

export default Summary;
