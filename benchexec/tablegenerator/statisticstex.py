# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import copy
import logging
import re
from collections import Counter, defaultdict
from typing import List, Iterable, Set, Any

from benchexec.tablegenerator.columns import Column, ColumnType

from benchexec.tablegenerator import util
from benchexec.tablegenerator.statistics import ColumnStatistics, StatValue

TEX_HEADER = r"""% Statistics produced by BenchExec, more information at
% https://github.com/sosy-lab/benchexec/blob/main/doc/table-generator.md
% By default, this file defines a LaTeX command for each statistics value
% where the command name consists of the following concatenated parts:
% benchmark name, runset name, column title, category, status, statistic.
% (If necessary, this can be overridden with
% \newcommand\StoreBenchExecResult[7]{...} before including this file.)
% Numbers are replaced by roman numerals, all parts of the name are in camel case,
% and if necessary for uniqueness a counter is appended to the non-unique name part.
% The last part of the name is either "Count", "Sum", "Min", "Max", "Avg", "Median",
% "Stdev", "Score", or "Unit", with the latter providing the unit for the others.
% Rounding of values can be specified in the BenchExec table definition or done with
% \usepackage[round-mode=figures, round-precision=...]{siunitx} and the \num command.
% Arguments: benchmark name, runset name, column title, category, status, statistic, value
\providecommand\StoreBenchExecResult[7]{\expandafter\newcommand\csname#1#2#3#4#5#6\endcsname{#7}}%
"""

RENAME_FUNCTIONS = {
    "column": lambda value: "all" if value.lower() == "total" else value,
}


class LatexCommand:
    """Data holder for latex command."""

    def __init__(self, benchmark_name="", runset_name=""):
        self.benchmark_name = LatexCommand.format_command_part(str(benchmark_name))
        self.runset_name = LatexCommand.format_command_part(str(runset_name))
        self.column_title = ""
        self.column = ""
        self.status = ""
        self.stat_type = ""
        self.value = None

    def set_command_part(self, part_name: str, part_value) -> "LatexCommand":
        """Sets the value of the command part

        Available part names:
            benchmark_name, runset_name, column_title, column, status, stat_type

        Args:
            part_name: One of the names above
            part_value: The value to be set for this command part

        Returns:
            This LatexCommand
        """
        if part_name in RENAME_FUNCTIONS.keys():
            part_value = RENAME_FUNCTIONS[part_name](part_value)
        self.__dict__[part_name] = LatexCommand.format_command_part(str(part_value))
        return self

    def set_command_value(self, value: Any) -> "LatexCommand":
        """Sets the value for this command

        The value will be converted to a string. No checks are made in this method.
        If any special format is necessary, please call this method with the formatted value.

        Args:
            value: The new command value
        Returns:
            This LatexCommand
        """
        if value is None:
            value = ""
        self.value = str(value)
        return self

    def to_latex_raw(self) -> str:
        """Prints latex command with raw value (e.g. only number, no additional latex command)."""
        return f"{self}{{{self.value}}}"

    def to_latex_score_as_stat_type(self) -> str:
        """Raw output except the score, which is used as stat_type"""
        if self.column.lower() != "score":
            return self.to_latex_raw()

        # save original values
        score = self.column
        score_type = self.stat_type

        self.column = LatexCommand.format_command_part("all")
        self.stat_type = score

        command_as_string = self.to_latex_raw()

        # restore the original state
        self.column = score
        self.stat_type = score_type

        return command_as_string

    def __repr__(self):
        return "\\StoreBenchExecResult{%s}{%s}{%s}{%s}{%s}{%s}" % (
            self.benchmark_name,
            self.runset_name,
            self.column_title,
            self.column,
            self.status,
            self.stat_type,
        )

    @staticmethod
    def format_command_part(name: str) -> str:
        name = re.sub(
            # Matches only positive numbers, because 0 can't be converted to roman number
            "[1-9]\\d*",
            lambda match: util.number_to_roman_string(match.group()),
            name,
        )

        name = re.split("[^a-zA-Z]", name)

        name = "".join(util.cap_first_letter(word) for word in name)

        return name


def write_tex_command_table(
    out,
    run_sets: List,
    stats: List[List[ColumnStatistics]],
    **kwargs,
):
    # Saving the formatted benchmarkname and niceName with the id of the runset to prevent latter formatting
    formatted_names = {}
    for run_set in run_sets:
        benchmark_name_formatted = LatexCommand.format_command_part(
            run_set.attributes["benchmarkname"]
        )
        runset_name_formatted = LatexCommand.format_command_part(
            # name can be a list
            "".join(run_set.attributes["name"])
        )
        formatted_names[id(run_set)] = benchmark_name_formatted, runset_name_formatted

    # Counts the total number of benchmarkname and niceName combinations
    names_total_counts = Counter(formatted_names.values())

    # Counts the actual used benchmarkname and niceName combinations
    names_already_used = defaultdict(int)

    # Filtering all candidates for skipping
    skipped_columns = {"correct_unconfirmed"}
    skipped_columns = {
        column
        for column in skipped_columns
        if not _statistics_has_value_for(stats, column)
    }

    out.write(TEX_HEADER)
    for run_set, stat_list in zip(run_sets, stats):
        name_tuple = formatted_names[id(run_set)]

        # Increasing the count before the check to add suffix 1 to the first encounter of a duplicated
        # benchmarkname + niceName combination
        names_already_used[name_tuple] += 1
        benchmark_name_formatted, runset_name_formatted = name_tuple

        # Duplication detected, adding suffix to benchmarkname
        if names_total_counts[name_tuple] > 1:
            suffix = util.number_to_roman_string(names_already_used[name_tuple])
            logging.warning(
                'Duplicated formatted benchmark name + runset name "%s" detected. '
                "The combination of names must be unique for Latex. "
                "Adding suffix %s to benchmark name",
                benchmark_name_formatted + runset_name_formatted,
                suffix,
            )
            benchmark_name_formatted += suffix

        command = LatexCommand(benchmark_name_formatted, runset_name_formatted)

        for latex_command in _provide_latex_commands(
            run_set, stat_list, command, skipped_columns
        ):
            out.write(latex_command.to_latex_score_as_stat_type())
            out.write("%\n")


def _statistics_has_value_for(
    all_column_stats: List[List[ColumnStatistics]], field: str
):
    """Checks the appearance of the given field in at least one of the given ColumnStatistics

    Args:
        all_column_stats: The ColumnsStatistics which may contain the given field
        field: The field that is searched

    Returns:
        True if the given field appears in at least one of the given ColumnStatistics

    """
    for run_set_stats in all_column_stats:
        for column_stats in run_set_stats:
            if column_stats:
                stats = getattr(column_stats, field)
                if stats and stats.sum > 0:
                    return True
    return False


def _provide_latex_commands(
    run_set,
    stat_list: List[ColumnStatistics],
    current_command: LatexCommand,
    skipped_columns: Set[str],
) -> Iterable[LatexCommand]:
    """
    Provides all LatexCommands for a given run_set + stat_list combination

    Args:
        run_set: A RunSetResult object
        stat_list: List of ColumnStatistics for each column in run_set
        current_command: LatexCommand with benchmark_name and displayName already filled
        skipped_columns: Set with all columns, which should be skipped

    Yields:
        All LatexCommands from the run_set + stat_list combination
    """

    # Preferring the display title over the standard title of a column to allow
    # custom titles defined by the user
    def select_column_name(col):
        return col.display_title or col.title

    column_titles_total_count = Counter(
        select_column_name(column) for column in run_set.columns
    )
    column_titles_already_used = defaultdict(int)

    for column, column_stats in zip(run_set.columns, stat_list):
        column_title = select_column_name(column)

        # Increasing the count before the check to add suffix 1 to the first encounter of a duplicated
        # column title
        column_titles_already_used[column_title] += 1

        if column_titles_total_count[column_title] > 1:
            suffix = util.number_to_roman_string(
                column_titles_already_used[column_title]
            )
            logging.warning(
                'Duplicated formatted column name "%s" detected! '
                "Column names must be unique for Latex. "
                "Adding suffix %s to column for now",
                column_title,
                suffix,
            )
            column_title += suffix

        current_command.set_command_part("column_title", column_title)

        yield from _column_statistic_to_latex_command(
            current_command, column_stats, column, skipped_columns
        )


def _column_statistic_to_latex_command(
    init_command: LatexCommand,
    column_statistic: ColumnStatistics,
    parent_column: Column,
    skipped_columns: Set[str],
) -> Iterable[LatexCommand]:
    """Parses a ColumnStatistics to Latex Commands and yields them

    The provided LatexCommand must have specified benchmark_name, display_name and column_name.

    Args:
        init_command: LatexCommand with not empty benchmark_name and display_name
        column_statistic: ColumnStatistics to convert to LatexCommand
        parent_column: Current column with meta-data
        skipped_columns: Set with all columns, which should be skipped
    Yields:
        A completely filled LatexCommand
    """
    if not column_statistic:
        return

    stat_value: StatValue
    for stat_name, stat_value in column_statistic.__dict__.items():
        if stat_value is None:
            continue

        column_parts = stat_name.rsplit("_", 1)
        # If the stat_name is not ending with true or false, use the whole stat_name as column and an empty string
        # as column_subcategory
        if column_parts[-1].lower() in ["true", "false"]:
            status = column_parts[-1]
            column_list = column_parts[0:-1]
        else:
            status = ""
            column_list = column_parts

        # Joining the column together to get the name original name
        if "_".join(column_list) in skipped_columns:
            continue

        # Copy command to prevent using filled command parts from previous iterations
        command = copy.deepcopy(init_command)

        # Some colum_categories use _ in their names, that's why the column_category is the
        # whole split list except the last word
        command.set_command_part(
            "column",
            "".join(util.cap_first_letter(column_part) for column_part in column_list),
        )
        command.set_command_part("status", status)

        for k, v in stat_value.__dict__.items():
            # "v is None" instead of "if not v" used to allow number 0
            if v is None:
                continue

            if k == "sum":
                # Renaming sum to count for status type columns
                if parent_column.type == ColumnType.status:
                    k = "count"
                else:
                    assert parent_column.is_numeric()

            command.set_command_part("stat_type", k)
            command.set_command_value(
                parent_column.format_value(value=v, format_target="csv")
            )
            yield command
        if parent_column.unit:
            command.set_command_part("stat_type", "unit")
            command.set_command_value(parent_column.unit)
            yield command
