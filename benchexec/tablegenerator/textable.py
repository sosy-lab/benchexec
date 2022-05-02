import decimal
import logging
import re
from typing import List, Iterable, Callable, Dict

from benchexec.tablegenerator.columns import Column

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

    def set_command_value(self, value) -> "LatexCommand":
        """Sets the value for this command

        Args:
            value: The new command value
            scale_factor: Scaling factor for the new value
            value_data: Remaining unused value_data

        Returns:
            This LatexCommand
        """
        self.value = decimal.Decimal(value)
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


class DuplicationHolder:
    """Holds the total and used count of the duplication and the duplication itself"""

    def __init__(self, duplication: str):
        self.count = 0
        self.used = 0
        self.duplication = duplication


def create_duplication_dictionary(
    iterable: Iterable, pre_process: Callable = lambda x: x
) -> Dict[str, DuplicationHolder]:
    """Create a dictionary containing all the duplications of the iterable

    The preprocess function is evaluated before the actual evaluation to select custom duplication rules.
    For example, if the iterable some objects and you want a specific variable the pre_process function could look like:
        lambda object: object.variable

    Per default, the pre_process function is the identity

    Args:
        iterable: The iterable to check for duplications
        pre_process: A function, which is evaluated on each element before the actual duplication check

    Returns:
        A dictionary, containing a DuplicationHolder for each element with its respective count

    """
    return_dict = {}
    for element in iterable:
        selected_element = pre_process(element)

        if selected_element not in return_dict:
            return_dict[selected_element] = DuplicationHolder(selected_element)

        duplication_holder = return_dict[selected_element]
        duplication_holder.count += 1
    return return_dict


def combine_benchmarkname_displayName(run_set):
    benchmark_name_formatted = LatexCommand.format_command_part(
        run_set.attributes["benchmarkname"]
    )
    display_name_formatted = LatexCommand.format_command_part(
        run_set.attributes["displayName"]
    )
    return benchmark_name_formatted + display_name_formatted


def write_tex_command_table(
    out,
    run_sets: List,
    stats: List[List[ColumnStatistics]],
    **kwargs,
):
    # Check for duplicated benchmarkname + displayName
    benchmark_name_dict = create_duplication_dictionary(
        run_sets, combine_benchmarkname_displayName
    )

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

        # Duplication detected, adding suffix to benchmark_name
        if benchmark_name_holder.count > 1:
            suffix = util.number_to_roman_string(benchmark_name_holder.used)
            logging.warning(
                'Duplicated formatted benchmark name + displayName "%s" detected. '
                "The combination of names must be unique for Latex. "
                "Adding suffix %s to benchmark name",
                benchmark_name_holder.duplication,
                suffix,
            )
            benchmark_name_formatted += suffix

        command = LatexCommand(benchmark_name_formatted, display_name_formatted)

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

    def select_column_name(col):
        return col.display_title if col.display_title else col.title

    # Saves used columns and their amount
    used_column_titles = create_duplication_dictionary(
        run_set.columns, select_column_name
    )

    for column, column_stats in zip(run_set.columns, stat_list):
        column_title = select_column_name(column)
        duplication_holder = used_column_titles[column_title]
        duplication_holder.used += 1

        if duplication_holder.count > 1:
            suffix = util.number_to_roman_string(duplication_holder.used)
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
            current_command, column_stats, column
        )


def _column_statistic_to_latex_command(
    command: LatexCommand,
    column_statistic: ColumnStatistics,
    column: Column,
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
            yield command.set_command_value(
                column.format_value(value=v, format_target="raw")
            )
