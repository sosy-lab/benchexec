import copy
import decimal
import logging
import re
from collections import defaultdict
from typing import List, Iterable

from benchexec.tablegenerator import util
from benchexec.tablegenerator.statistics import ColumnStatistics, StatValue

TEX_HEADER = r"""% The following definition defines a command for each value.
% The command name is the concatenation of the first six arguments.
% To override this definition, define \StoreBenchExecResult with \newcommand before including this file.
% Arguments: benchmark name, run-set name, category, status, column name, statistic, value
\providecommand\StoreBenchExecResult[7]{\expandafter\newcommand\csname#1#2#3#4#5#6\endcsname{#7}}%
"""


class LatexCommand:
    """Data holder for latex command."""

    def __init__(self, benchmark_name="", display_name=""):
        self.benchmark_name = LatexCommand.format_command_part(str(benchmark_name))
        self.display_name = LatexCommand.format_command_part(str(display_name))
        self.column_title = ""
        self.column_category = ""
        self.column_subcategory = ""
        self.stat_type = ""
        self.value = None

    def set_command_part(self, part_name: str, part_value) -> "LatexCommand":
        """Sets the value of the command part

        Available part names:
            benchmark_name, display_name, column_title, column_category, column_subcategory, stat_type

        Args:
            part_name: One of the names above
            part_value: The value to be set for this command part

        Returns:
            This LatexCommand
        """
        self.__dict__[part_name] = LatexCommand.format_command_part(str(part_value))
        return self

    def set_command_value(self, value, scale_factor, **value_data) -> "LatexCommand":
        """Sets the value for this command

        Args:
            value: The new command value
            scale_factor: Scaling factor for the new value
            value_data: Remaining unused value_data

        Returns:
            This LatexCommand
        """
        self.value = decimal.Decimal(value)
        self.value *= scale_factor
        return self

    def to_latex_raw(self) -> str:
        """Prints latex command with raw value (e.g. only number, no additional latex command)."""
        return self._get_command_formatted(util.print_decimal(self.value))

    def __repr__(self):
        return "\\StoreBenchExecResult{%s}{%s}{%s}{%s}{%s}{%s}" % (
            self.benchmark_name,
            self.display_name,
            self.column_title,
            self.column_category,
            self.column_subcategory,
            self.stat_type,
        )

    def _get_command_formatted(self, value: str) -> str:
        """Formats the command with all parts and appends the value

        To use a custom format for the value, for example
            \\StoreBenchExecResult{some}{stuff}...{last_name_part}{\\textbf{value}}
        format the value and give it to this function
        """
        if not value:
            logging.warning(
                "Trying to print latex command without value! Using EMPTY value for command:\n %s"
                % self
            )
            value = ""
        return str(self) + "{%s}" % value

    @staticmethod
    def format_command_part(name: str) -> str:
        name = re.sub(
            "[0-9]+", lambda match: util.number_to_roman_string(match.group()), name
        )

        name = re.split("[^a-zA-Z]", name)

        name = "".join(util.cap_first_letter(word) for word in name)

        return name


class BenchNameHolder:
    """Holds the total and used count of the used benchmark_name + display_name combination"""

    def __init__(self, benchmark_name: str, display_name: str):
        self.count = 0
        self.used = 0
        self.combined_name = benchmark_name + display_name


def write_tex_command_table(
    out,
    run_sets: List,
    stats: List[List[ColumnStatistics]],
    **kwargs,
):
    # Check for duplicated benchmarkname + displayName
    # Increasing count if duplicated usage is detected
    # Iterating once through the run_sets to detect the total count of duplications in order that every
    # benchmark_name can get a suffix if duplicated
    benchmark_name_dict = {}
    for run_set in run_sets:
        # Need to use formatted name, because only then duplication detection is useful
        benchmark_name_formatted = LatexCommand.format_command_part(
            run_set.attributes["benchmarkname"]
        )
        display_name_formatted = LatexCommand.format_command_part(
            run_set.attributes["displayName"]
        )
        combined_name = benchmark_name_formatted + display_name_formatted
        if combined_name not in benchmark_name_dict:
            benchmark_name_dict[combined_name] = BenchNameHolder(
                benchmark_name_formatted, display_name_formatted
            )

        benchmark_name_holder = benchmark_name_dict[combined_name]
        benchmark_name_holder.count += 1

    out.write(TEX_HEADER)
    for run_set, stat_list in zip(run_sets, stats):
        benchmark_name_formatted = LatexCommand.format_command_part(
            run_set.attributes["benchmarkname"]
        )
        display_name_formatted = LatexCommand.format_command_part(
            run_set.attributes["displayName"]
        )

        benchmark_name_holder = benchmark_name_dict[
            benchmark_name_formatted + display_name_formatted
        ]

        benchmark_name_holder.used += 1
        suffix = ""
        if benchmark_name_holder.count > 1:
            suffix = util.number_to_roman_string(benchmark_name_holder.used)
            logging.warning(
                "Duplicated formatted benchmark name + displayName %s detected. "
                "The combination of names must be unique for Latex"
                "\nAdding suffix %s to benchmark name",
                benchmark_name_holder.combined_name,
                suffix,
            )
        command = LatexCommand(
            benchmark_name_formatted + suffix, display_name_formatted
        )

        for latex_command in _provide_latex_commands(run_set, stat_list, command):
            out.write(latex_command.to_latex_raw())
            out.write("%\n")


def _provide_latex_commands(
    run_set, stat_list: List[ColumnStatistics], current_command: LatexCommand
) -> Iterable[LatexCommand]:
    """
    Provides all LatexCommands for a given run_set + stat_list combination

    Args:
        run_set: A RunSetResult object
        stat_list: List of ColumnStatistics for each column in run_set
        current_command: LatexCommand with benchmark_name and displayName already filled

    Returns:
        Yields all LatexCommands from the run_set + stat_list combination
    """
    # Saves used columns and their amount
    used_column_titles = defaultdict(int)
    for column, column_stats in zip(run_set.columns, stat_list):
        column_title = column.display_title if column.display_title else column.title
        if column_title in used_column_titles:
            used_column_titles[column_title] += 1
            logging.warning(
                "Detected already used %s! "
                "Columns should be unique, please consider changing the name or displayTitle of this column \n"
                "Adding suffix %s to column %s for now",
                column_title,
                used_column_titles[column_title],
                column_title,
            )
            column_title += str(used_column_titles[column_title])

        used_column_titles[column_title] += 1
        current_command.set_command_part("column_title", column_title)

        yield from _column_statistic_to_latex_command(
            current_command, column_stats, **column.__dict__
        )


def _column_statistic_to_latex_command(
    command: LatexCommand,
    column_statistic: ColumnStatistics,
    **value_data,
) -> Iterable[LatexCommand]:
    """Parses a ColumnStatistics to Latex Commands and appends them to the given command_list

    The provided LatexCommand must have specified benchmark_name and display_name.

    Args:
        command: LatexCommand with not empty benchmark_name and display_name
        column_statistic: ColumnStatistics to convert to LatexCommand
        command_list: List of LatexCommands
    """
    if not column_statistic:
        return

    stat_value: StatValue
    for stat_name, stat_value in column_statistic.__dict__.items():
        if stat_value is None:
            continue
        column_parts = stat_name.split("_")
        if len(column_parts) < 2:
            column_parts.append("")

        # Some colum_categories use _ in their names, that's why the column_category is the
        # whole split list except the last word
        command.set_command_part(
            "column_category",
            "".join(
                util.cap_first_letter(column_part) for column_part in column_parts[0:-1]
            ),
        ).set_command_part("column_subcategory", column_parts[-1])

        for k, v in stat_value.__dict__.items():
            # "v is None" instead of "if not v" used to allow number 0
            if v is None:
                continue
            command.set_command_part("stat_type", k)
            yield copy.deepcopy(command).set_command_value(v, **value_data)
