# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import collections
import copy
import json
import logging
import os
from urllib.parse import quote as url_quote

from benchexec import __version__
from benchexec.tablegenerator import util
import benchexec.util

_REACT_FILES = [
    os.path.join(os.path.dirname(__file__), "react-table", "build", path)
    for path in ["vendors.min.", "main.min."]
]


def write_html_table(
    out,
    options,
    title,
    run_sets,
    rows,
    stats,
    relevant_id_columns,
    output_path,
    common_prefix,
    **kwargs,
):
    app_css = [util.read_bundled_file(path + "css") for path in _REACT_FILES]
    app_js = [util.read_bundled_file(path + "js") for path in _REACT_FILES]
    benchmark_setup = _prepare_benchmark_setup_data(
        run_sets, common_prefix, relevant_id_columns
    )
    columns = [run_set.columns for run_set in run_sets]
    stats = _prepare_stats(stats, rows, columns)
    tools = _prepare_run_sets_for_js(run_sets)
    href_base = os.path.dirname(options.xmltablefile) if options.xmltablefile else None
    rows_js = _prepare_rows_for_js(rows, output_path, href_base, relevant_id_columns)
    initial_state = options.initial_table_state

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
        f"""<!DOCTYPE html>
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8">
<meta name="generator" content="BenchExec table-generator {__version__}">
<title>{title} &ndash; BenchExec results</title>

"""
    )
    write_tags("style", app_css)
    out.write(
        """<style>
    #msg-container {
        text-align: center;
        margin-top: 2rem;
        font-size: 1.2rem;
    }
</style>
</head>

<body>

<div id="msg-container">
    Please wait while the page is being loaded.
</div>
<div id="root">
</div>
<noscript>
  This is an interactive table for viewing results produced by
  <a href="https://github.com/sosy-lab/benchexec" target="_blank" rel="noopener noreferrer">BenchExec</a>.
  Please enable JavaScript to use it.
</noscript>
<script>
    try {
        [0].flat();
    } catch (err) {
        var msgContainer = document.getElementById("msg-container");
        msgContainer.innerHTML = "Your browser is not supported. Please consider using another browser such as Firefox or Google Chrome."
    }
</script>
<script>
const data = {
"""
    )
    write_json_part("version", __version__)
    write_json_part("head", benchmark_setup)
    write_json_part("tools", tools)
    write_json_part("rows", rows_js)
    write_json_part("initial", initial_state)
    write_json_part("stats", stats, last=True)
    out.write(
        """};
window.data = data;
</script>

"""
    )
    write_tags("script", app_js)
    out.write("</body>\n</html>\n")


def _prepare_benchmark_setup_data(
    runSetResults, commonFileNamePrefix, relevant_id_columns
):
    # This list contains the number of columns each run set has
    # (the width of a run set in the final table)
    # It is used for calculating the column spans of the header cells.
    runSetWidths = [len(runSetResult.columns) for runSetResult in runSetResults]

    def format_string_cell(attributes, format_string, onlyIf=None, default="Unknown"):
        if onlyIf and onlyIf not in attributes:
            formatStr = default
        else:
            formatStr = format_string
        return formatStr.format_map(collections.defaultdict(str, attributes))

    def tool_data_cell(attributes):
        keys = ["tool", "version", "project_url", "version_url"]
        return {k: str(attributes[k]) for k in keys if attributes.get(k)}

    def get_row(
        rowName,
        *format_args,
        cell_format=format_string_cell,
        collapse=False,
        **format_kwargs,
    ):
        values = [
            cell_format(runSetResult.attributes, *format_args, **format_kwargs)
            for runSetResult in runSetResults
        ]
        if not any(values):
            return None  # skip row without values completely

        valuesAndWidths = (
            list(util.collapse_equal_values(values, runSetWidths))
            if collapse
            else list(zip(values, runSetWidths))
        )

        return dict(  # noqa: C408
            id=rowName.lower().split(" ")[0], name=rowName, content=valuesAndWidths
        )

    titles = [
        column.format_title()
        for runSetResult in runSetResults
        for column in runSetResult.columns
    ]
    runSetWidths1 = [1] * sum(runSetWidths)
    titleRow = dict(  # noqa: C408
        id="columnTitles",
        # commonFileNamePrefix may contain paths, so standardize the output across OSs
        name=util.fix_path_if_on_windows(commonFileNamePrefix),
        content=list(zip(titles, runSetWidths1)),
    )

    property_row = None
    if not relevant_id_columns[1]:  # property is the same for all tasks
        common_property = runSetResults[0].results[0].task_id[1]
        if common_property:
            property_row = dict(  # noqa: C408
                id="property",
                name="Properties",
                content=[[common_property.name, sum(runSetWidths)]],
            )

    return {
        "tool": get_row("Tool", cell_format=tool_data_cell, collapse=True),
        "displayName": get_row("Benchmark", "{displayName}", collapse=True),
        "limit": get_row(
            "Limits",
            "timelimit: {timelimit}, memlimit: {memlimit}, CPU core limit: {cpuCores}",
            collapse=True,
        ),
        "host": get_row("Host", "{host}", collapse=True, onlyIf="host"),
        "os": get_row("OS", "{os}", collapse=True, onlyIf="os"),
        "system": get_row(
            "System",
            "CPU: {cpu}, cores: {cores}, frequency: {freq}{turbo}; RAM: {ram}",
            collapse=True,
            onlyIf="cpu",
        ),
        "date": get_row("Date of execution", "{date}", collapse=True),
        "runset": get_row("Run set", "{niceName}"),
        "branch": get_row("Branch", "{branch}"),
        "options": get_row("Options", "{options}"),
        "property": property_row,
        "title": titleRow,
        "task_id_names": [
            name
            for name, selected in zip(util.TaskId.field_names, relevant_id_columns)
            if selected
        ],
    }


def _get_task_counts(rows):
    """Calculcate number of true/false tasks and maximum achievable score."""
    count_true = count_false = 0
    max_score = None
    for row in rows:
        if not row.id.property:
            logging.debug("Missing property for task %s.", row.id)
            continue
        expected_result = row.id.expected_result
        if not expected_result:
            continue
        if expected_result.result is True:
            count_true += 1
        elif expected_result.result is False:
            count_false += 1
        row_max_score = row.id.property.max_score(
            expected_result, row.id.witness_category
        )
        if row_max_score is not None:
            max_score = row_max_score + (max_score or 0)

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
            return column.format_value(value, "html_cell")
        elif key == "avg" or key == "stdev":
            return column.format_value(value, "tooltip_stochastic")
        else:
            return column.format_value(value, "tooltip")

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

    # Column instances contain the info about how to format (round and align) values.
    # However, alignment info is based on the values in the actual table, whereas for
    # the stats table often less whitespace for alignment is necessary.
    # So we replace the Column instances with adjusted ones.
    def adjust_column_to_statistics_values(column, column_stats):
        if not column_stats:
            return column
        # Compute alignment info from the values shown in the statistics table (sums).
        values = [stat.sum for stat in column_stats.__dict__.values() if stat]
        new_column = copy.copy(column)
        new_column.set_column_type_from(values)
        return new_column

    columns = [
        [
            adjust_column_to_statistics_values(column, column_stats)
            for column_stats, column in zip(run_set_stats, run_set_columns)
        ]
        for run_set_stats, run_set_columns in zip(all_column_stats, columns)
    ]

    task_counts = (
        f"in total {count_true} true tasks, {count_false} false tasks"
        if count_true or count_false
        else ""
    )

    stat_rows = []

    def add_stat_row(field, title=None, description=None):
        content = [
            [
                _convert_statvalue_to_json(column_stats, field, column)
                for column_stats, column in zip(run_set_stats, run_set_columns)
            ]
            for run_set_stats, run_set_columns in zip(all_column_stats, columns)
        ]
        row = {"id": field, "content": content}
        if title:
            row["title"] = title
        if description:
            row["description"] = description
        stat_rows.append(row)

    add_stat_row("total", description=task_counts)

    if _statistics_has_value_for(all_column_stats, "local"):
        add_stat_row(
            "local",
            "local summary",
            "(This line contains some statistics from local execution. "
            "Only trust those values, if you use your own computer.)",
        )

    has_correct = _statistics_has_value_for(all_column_stats, "correct")
    has_wrong = _statistics_has_value_for(all_column_stats, "wrong")
    if has_correct or has_wrong:
        add_stat_row("correct")
        add_stat_row("correct_true")
        add_stat_row("correct_false")

        if _statistics_has_value_for(all_column_stats, "correct_unconfirmed"):
            add_stat_row("correct_unconfirmed")
            add_stat_row("correct_unconfirmed_true")
            add_stat_row("correct_unconfirmed_false")

        add_stat_row("wrong")
        add_stat_row("wrong_true")
        add_stat_row("wrong_false")

    if max_score is not None:
        add_stat_row(
            "score", f"score ({len(rows)} tasks, max score: {max_score})", task_counts
        )

    return stat_rows


def _prepare_run_sets_for_js(run_sets):
    # Almost all run_set attributes are relevant, use blacklist here
    run_set_exclude_keys = {"filename"}

    def prepare_column(column):
        result = {k: v for k, v in column.__dict__.items() if v is not None}
        result.pop("scale_factor", None)
        result.pop("source_unit", None)
        if "href" in result:
            # href may contain an url created from an os-dependant path, so standardize it between OSs
            result["href"] = util.fix_path_if_on_windows(result["href"])
        result["display_title"] = column.display_title or column.title
        result["type"] = column.type.type.name
        number_of_significant_digits = column.get_number_of_significant_digits()
        if number_of_significant_digits is not None:
            result["number_of_significant_digits"] = number_of_significant_digits
        return result

    def prepare_run_set(attributes, columns):
        result = {
            k: v for k, v in attributes.items() if k not in run_set_exclude_keys and v
        }
        result["columns"] = [prepare_column(col) for col in columns]
        return result

    return [prepare_run_set(rs.attributes, rs.columns) for rs in run_sets]


def _prepare_rows_for_js(rows, base_dir, href_base, relevant_id_columns):
    results_include_keys = ["category", "score"]

    def prepare_value(column, value, run_result):
        """
        Return a dict that represents one value (table cell).
        We always add the raw value (never rounded), and sometimes a version that is
        formatted for HTML (e.g., with spaces for alignment).
        """
        raw_value = column.format_value(value, "raw")
        # We need to make sure that formatted_value is safe (no unescaped tool output),
        # but for text columns format_value returns the same for csv and html_cell,
        # and for number columns the HTML result is safe.
        formatted_value = column.format_value(value, "html_cell")
        result = {}
        if column.href:
            result["href"] = _create_link(column.href, base_dir, run_result, href_base)
            if not raw_value and not formatted_value:
                raw_value = column.pattern
        if raw_value is not None and not raw_value == "":
            result["raw"] = raw_value
        if formatted_value and formatted_value != raw_value:
            result["html"] = formatted_value
        return result

    def clean_up_results(res):
        values = [
            prepare_value(column, value, res)
            for column, value in zip(res.columns, res.values)
        ]
        hrefs = (
            column.href for column in res.columns if column.title.endswith("status")
        )
        toolHref = next(hrefs, None) or res.log_file
        result = {
            k: getattr(res, k)
            for k in results_include_keys
            if getattr(res, k) is not None
        }
        if toolHref:
            result["href"] = _create_link(toolHref, base_dir, res, href_base)
        result["values"] = values
        return result

    def clean_up_row(row):
        result = {}
        result["id"] = [
            str(id_part)
            for id_part, relevant in zip(row.id, relevant_id_columns)
            if id_part and relevant
        ]
        # Replace first part of id (task name, which is always shown) with short name
        assert relevant_id_columns[0]
        # row.short_filename may contain paths, so standardize the output across OSs
        result["id"][0] = util.fix_path_if_on_windows(row.short_filename)

        result["results"] = [clean_up_results(res) for res in row.results]
        if row.has_sourcefile:
            result["href"] = _create_link(row.id.name, base_dir)
        return result

    return [clean_up_row(row) for row in rows]


def _create_link(href, base_dir, runResult=None, href_base=None):
    def get_replacements(task_file):
        var_prefix = "taskdef_" if task_file.endswith(".yml") else "inputfile_"
        return [
            (var_prefix + "name", os.path.basename(task_file)),
            (var_prefix + "path", os.path.dirname(task_file) or "."),
            (var_prefix + "path_abs", os.path.dirname(os.path.abspath(task_file))),
        ] + (
            [
                ("logfile_name", os.path.basename(runResult.log_file)),
                (
                    "logfile_path",
                    os.path.dirname(
                        os.path.relpath(runResult.log_file, href_base or ".")
                    )
                    or ".",
                ),
                (
                    "logfile_path_abs",
                    os.path.dirname(os.path.abspath(runResult.log_file)),
                ),
            ]
            if runResult.log_file
            else []
        )

    source_file = (
        # os.path.relpath creates os-dependant paths, so standardize the output between OSs
        util.fix_path_if_on_windows(
            os.path.relpath(runResult.task_id.name, href_base or ".")
        )
        if runResult
        else None
    )

    if benchexec.util.is_url(href):
        # quote special characters only in inserted variable values, not full URL
        if source_file:
            source_file = url_quote(source_file)
            href = benchexec.util.substitute_vars(href, get_replacements(source_file))
        return href

    # quote special characters everywhere (but not twice in source_file!)
    if source_file:
        href = benchexec.util.substitute_vars(href, get_replacements(source_file))
    # os.path.relpath creates os-dependant paths, so standardize the output between OSs
    return url_quote(util.fix_path_if_on_windows(os.path.relpath(href, base_dir)))
