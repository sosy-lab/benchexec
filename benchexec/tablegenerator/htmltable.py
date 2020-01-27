# BenchExec is a framework for reliable benchmarking.
# This file is part of BenchExec.
#
# Copyright (C) 2007-2019  Dirk Beyer
# All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import logging
import os

from benchexec import __version__
from benchexec.tablegenerator import util

_REACT_FILES = [
    os.path.join(os.path.dirname(__file__), "react-table", "build", path)
    for path in ["vendors.min.", "bundle.min."]
]


def write_html_table(
    out,
    options,
    title,
    head,
    run_sets,
    rows,
    stats,
    relevant_id_columns,
    output_path,
    **kwargs,
):
    app_css = [util.read_bundled_file(path + "css") for path in _REACT_FILES]
    app_js = [util.read_bundled_file(path + "js") for path in _REACT_FILES]
    columns = [run_set.columns for run_set in run_sets]
    stats = _prepare_stats(stats, rows, columns)
    tools = util.prepare_run_sets_for_js(run_sets)
    href_base = os.path.dirname(options.xmltablefile) if options.xmltablefile else None
    rows_js = util.prepare_rows_for_js(
        rows, output_path, href_base, relevant_id_columns
    )

    def write_tags(tag_name, contents):
        for content in contents:
            out.write("<")
            out.write(tag_name)
            out.write(">\n")
            out.write(content)
            out.write("\n</")
            out.write(tag_name)
            out.write(">\n")

    def write_json_part(name, value=None, last=False):
        out.write('  "')
        out.write(name)
        out.write('": ')
        out.write(json.dumps(value, sort_keys=True))
        if not last:
            out.write(",")
        out.write("\n")

    out.write(
        """<!DOCTYPE html>
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8">
<meta name="generator" content="BenchExec table-generator {version}">
<title>{title} &ndash; BenchExec results</title>

""".format(
            title=title, version=__version__
        )
    )
    write_tags("style", app_css)
    out.write(
        """</head>
<body>

<div id="root"></div>
<noscript>
  This is an interactive table for viewing results produced by
  <a href="https://github.com/sosy-lab/benchexec" target="_blank" rel="noopener noreferrer">BenchExec</a>.
  Please enable JavaScript to use it.
</noscript>

<script>
const data = {
"""
    )
    write_json_part("version", __version__)
    write_json_part("head", head)
    write_json_part("tools", tools)
    write_json_part("rows", rows_js)
    write_json_part("stats", stats, last=True)
    out.write(
        """};
window.data = data;
</script>

"""
    )
    write_tags("script", app_js)
    out.write("</body>\n</html>\n")


def _get_task_counts(rows):
    """Calculcate number of true/false tasks and maximum achievable score."""
    count_true = count_false = max_score = 0
    for row in rows:
        if not row.properties:
            logging.info("Missing property for %s.", row.filename)
            continue
        if len(row.properties) > 1:
            # multiple properties not yet supported
            count_true = count_false = max_score = 0
            break
        expected_result = row.expected_results.get(row.properties[0].name)
        if not expected_result:
            continue
        if expected_result.result is True:
            count_true += 1
        elif expected_result.result is False:
            count_false += 1
        for prop in row.properties:
            max_score += prop.max_score(expected_result)

    return max_score, count_true, count_false


def _statistics_has_value_for(all_column_stats, field):
    for run_set_stats in all_column_stats:
        for column_stats in run_set_stats:
            if column_stats:
                stats = getattr(column_stats, field)
                if stats and stats.sum > 0:
                    return True
    return False


def _convert_statvalue_to_json(column_stats, field, column):
    def format_stat_value(key, value):
        if key == "sum":
            return column.format_value(value, True, "html_cell")
        else:
            return column.format_value(value, False, "tooltip")

    if column_stats is None:
        return None
    statvalue = getattr(column_stats, field)
    if statvalue is None:
        return None
    return {
        k: format_stat_value(k, v)
        for k, v in statvalue.__dict__.items()
        if v is not None
    }


def _prepare_stats(all_column_stats, rows, columns):
    max_score, count_true, count_false = _get_task_counts(rows)

    task_counts = (
        "in total {0} true tasks, {1} false tasks".format(count_true, count_false)
        if count_true or count_false
        else ""
    )

    def indent(n):
        return "&nbsp;" * (n * 4)

    def get_stat_row(field):
        return [
            [
                _convert_statvalue_to_json(column_stats, field, column)
                for column_stats, column in zip(run_set_stats, run_set_columns)
            ]
            for run_set_stats, run_set_columns in zip(all_column_stats, columns)
        ]

    stat_rows = [
        dict(  # noqa: C408
            id=None,
            title="total",
            description=task_counts,
            content=get_stat_row("total"),
        )
    ]

    if _statistics_has_value_for(all_column_stats, "local"):
        stat_rows.append(
            dict(  # noqa: C408
                id=None,
                title="local summary",
                description="(This line contains some statistics from local execution. Only trust those values, if you use your own computer.)",
                content=get_stat_row("local"),
            )
        )

    if count_true or count_false:
        stat_rows.append(
            dict(  # noqa: C408
                id=None,
                title=indent(1) + "correct results",
                description="(property holds + result is true) OR (property does not hold + result is false)",
                content=get_stat_row("correct"),
            )
        )
        stat_rows.append(
            dict(  # noqa: C408
                id=None,
                title=indent(2) + "correct true",
                description="property holds + result is true",
                content=get_stat_row("correct_true"),
            )
        )
        stat_rows.append(
            dict(  # noqa: C408
                id=None,
                title=indent(2) + "correct false",
                description="property does not hold + result is false",
                content=get_stat_row("correct_false"),
            )
        )

        if _statistics_has_value_for(all_column_stats, "correct_unconfirmed"):
            stat_rows.append(
                dict(  # noqa: C408
                    id=None,
                    title=indent(1) + "correct-unconfimed results",
                    description="(property holds + result is true) OR (property does not hold + result is false), but unconfirmed",
                    content=get_stat_row("correct_unconfirmed"),
                )
            )
            stat_rows.append(
                dict(  # noqa: C408
                    id=None,
                    title=indent(2) + "correct-unconfirmed true",
                    description="property holds + result is true, but unconfirmed",
                    content=get_stat_row("correct_unconfirmed_true"),
                )
            )
            stat_rows.append(
                dict(  # noqa: C408
                    id=None,
                    title=indent(2) + "correct-unconfirmed false",
                    description="property does not hold + result is false, but unconfirmed",
                    content=get_stat_row("correct_unconfirmed_false"),
                )
            )

        stat_rows.append(
            dict(  # noqa: C408
                id=None,
                title=indent(1) + "incorrect results",
                description="(property holds + result is false) OR (property does not hold + result is true)",
                content=get_stat_row("wrong"),
            )
        )
        stat_rows.append(
            dict(  # noqa: C408
                id=None,
                title=indent(2) + "incorrect true",
                description="property does not hold + result is true",
                content=get_stat_row("wrong_true"),
            )
        )
        stat_rows.append(
            dict(  # noqa: C408
                id=None,
                title=indent(2) + "incorrect false",
                description="property holds + result is false",
                content=get_stat_row("wrong_false"),
            )
        )

    if max_score:
        stat_rows.append(
            dict(  # noqa: C408
                id="score",
                title="score ({0} tasks, max score: {1})".format(len(rows), max_score),
                description=task_counts,
                content=get_stat_row("score"),
            )
        )

    return stat_rows
