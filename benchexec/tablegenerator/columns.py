# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import re
import decimal
from decimal import Decimal
import enum
from math import floor, ceil, log10
import logging
from typing import Tuple, Union

from benchexec.util import print_decimal
from benchexec.tablegenerator import util

__all__ = ["Column", "ColumnType", "ColumnMeasureType"]

# It's important to make sure on *all* entry points / methods which perform arithmetics that the correct
# rounding / context is used by using a local context.
DECIMAL_CONTEXT = decimal.Context(rounding=decimal.ROUND_HALF_UP)

DEFAULT_TIME_PRECISION = 3
DEFAULT_TOOLTIP_PRECISION = 2
# Compile regular expression for detecting measurements only once.
REGEX_MEASURE = re.compile(
    r"\s*([-\+])?(?:([Nn][aA][Nn]|[iI][nN][fF]|[iI][nN][fF][iI][nN][iI][tT][yY])|(\d+)(\.(0*)(\d+))?([eE]([-\+])(\d+))?\s?([a-zA-Z/%]*))\s*$"
)
GROUP_SIGN = 1
GROUP_SPECIAL_FLOATS_PART = 2
GROUP_INT_PART = 3
GROUP_DEC_PART = 4
GROUP_ZEROES = 5
GROUP_SIG_DEC_PART = 6
GROUP_EXPONENT_PART = 7
GROUP_EXPONENT_SIGN = 8
GROUP_EXPONENT_VALUE = 9
GROUP_UNIT = 10
POSSIBLE_FORMAT_TARGETS = [
    "html",
    "html_cell",
    "tooltip",
    "tooltip_stochastic",
    "csv",
    "raw",
]

DEFAULT_NUMBER_OF_SIGNIFICANT_DIGITS = 3

_ONE = Decimal(1)
UNIT_CONVERSION = {
    "s": {"ms": 1000, "min": _ONE / 60, "h": _ONE / 3600},
    "B": {"kB": Decimal("1e-3"), "MB": Decimal("1e-6"), "GB": Decimal("1e-9")},
    "J": {
        "kJ": _ONE / 10**3,
        "Ws": _ONE,
        "kWs": _ONE / 1000,
        "Wh": _ONE / 3600,
        "kWh": _ONE / (1000 * 3600),
        "mWh": _ONE / (1000 * 1000 * 3600),
    },
}

inf = Decimal("inf")


class ColumnType(enum.Enum):
    text = enum.auto()
    count = enum.auto()
    measure = enum.auto()
    status = enum.auto()

    @property
    def type(self):
        return self


class ColumnMeasureType(object):
    """
    Column type 'Measure', contains the column's unit and the largest amount of digits after the decimal point.
    """

    def __init__(self, max_decimal_digits):
        self._type = ColumnType.measure
        self._max_decimal_digits = max_decimal_digits

    @property
    def type(self):
        return self._type

    @property
    def max_decimal_digits(self):
        return self._max_decimal_digits

    def __str__(self):
        return f"{self._type}({self._max_decimal_digits})"


class Column(object):
    """
    The class Column contains title, pattern (to identify a line in log_file),
    number_of_significant_digits of a column, the type of the column's values,
    their unit, a scale factor to apply to all values of the column (mostly to fit the unit)
    and href (to create a link to a resource).
    It does NOT contain the value of a column.

    The following conditions must be kept, but cannot be checked in the constructor.
    If they are violated, they may lead to errors in other parts of the program.
    * If 'scale_factor' is a value other than the default, 'unit' must be set.
    * If 'unit' and 'scale_factor' are set, 'source_unit' must be set, or the column's cells must not have a
      source unit, i.e. the source unit "".
    * If set, 'source_unit' must fit the source unit of the column's cells.
    * In addition, if 'unit' and 'source_unit' are set and of different values,
      'scale_factor' must be a value other than 'None'.
    """

    def __init__(
        self,
        title,
        pattern=None,
        num_of_digits=None,
        href=None,
        col_type=None,
        unit=None,
        source_unit=None,
        scale_factor=None,
        relevant_for_diff=None,
        display_title=None,
    ):
        with decimal.localcontext(DECIMAL_CONTEXT):

            # If scaling on the variables is performed, a display unit must be defined, explicitly
            if scale_factor is not None and scale_factor != 1 and unit is None:
                raise util.TableDefinitionError(
                    f"Scale factor is defined, but display unit is not (in column {title})"
                )

            self.title = title
            self.pattern = pattern
            self.number_of_significant_digits = (
                int(num_of_digits) if num_of_digits else None
            )
            self.type = col_type
            self.unit = unit
            self.source_unit = source_unit
            self.scale_factor = Decimal(scale_factor) if scale_factor else scale_factor
            self.href = href
            if relevant_for_diff is None:
                self.relevant_for_diff = False
            else:
                self.relevant_for_diff = (
                    True if relevant_for_diff.lower() == "true" else False
                )
            self.display_title = display_title

            # expected maximum width (in characters)
            self.max_width = None

    def is_numeric(self):
        return (
            self.type.type == ColumnType.measure or self.type.type == ColumnType.count
        )

    def get_number_of_significant_digits(self, format_target=None):
        if format_target == "raw":
            return None
        number_of_significant_digits = self.number_of_significant_digits
        if self.type.type == ColumnType.measure:
            if number_of_significant_digits is None and format_target != "csv":
                number_of_significant_digits = DEFAULT_TIME_PRECISION
        return number_of_significant_digits

    def format_title(self):
        title = self.display_title or self.title
        if self.is_numeric() and (self.unit or self.source_unit):
            used_unit = self.unit or self.source_unit
            return f"{title} ({used_unit})"

        else:
            return title

    def format_value(self, value, format_target):
        """
        Format a value nicely for human-readable output (including rounding).

        @param value: the value to format
        @param format_target the target the value should be formatted for
        @return: a formatted String representation of the given value.
        """
        with decimal.localcontext(DECIMAL_CONTEXT):

            # Only format counts and measures
            if (
                self.type.type != ColumnType.count
                and self.type.type != ColumnType.measure
            ):
                return value

            if format_target not in POSSIBLE_FORMAT_TARGETS:
                raise ValueError("Unknown format target")

            if value is None or value == "":
                return ""

            if isinstance(value, str):
                # If the number ends with "s" or another unit, remove it.
                # Units should not occur in table cells, but in the table head.
                number_str = util.remove_unit(value.strip())
                number = Decimal(number_str)
            elif isinstance(value, Decimal):
                number = value
                number_str = print_decimal(number)
            else:
                raise TypeError(f"Unexpected number type {type(value)}")

            if number.is_nan():
                return "NaN"
            elif number == inf:
                return "Inf"
            elif number == -inf:
                return "-Inf"

            # Apply the scale factor to the value
            if self.scale_factor is not None:
                number *= self.scale_factor
            assert number.is_finite()

            if (
                self.number_of_significant_digits is None
                and self.type.type != ColumnType.measure
                and format_target == "tooltip_stochastic"
            ):
                # Column of type count (integral values) without specified sig. digits.
                # However, we need to round values like stdev, so we just round somehow.
                return print_decimal(round(number, DEFAULT_TOOLTIP_PRECISION))

            number_of_significant_digits = self.get_number_of_significant_digits(
                format_target
            )
            max_dec_digits = (
                self.type.max_decimal_digits
                if isinstance(self.type, ColumnMeasureType)
                else 0
            )

            if number_of_significant_digits is not None:
                current_significant_digits = _get_significant_digits(number_str)
                return _format_number(
                    number,
                    current_significant_digits,
                    number_of_significant_digits,
                    max_dec_digits,
                    format_target,
                )
            else:
                return print_decimal(number)

    def set_column_type_from(self, column_values):
        """
        Sets the type of this column using a heuristic reading the given column_values.
        """
        column_values = list(column_values)
        values_width = 0
        try:
            result = _get_column_type_heur(self, column_values)
            if isinstance(result, tuple):
                (
                    self.type,
                    self.unit,
                    self.source_unit,
                    self.scale_factor,
                    values_width,
                ) = result
            else:
                self.type = result
        except util.TableDefinitionError as e:
            logging.warning("Column type couldn't be determined: %s", e)
            self.type = ColumnType.text

        if not self.is_numeric():
            self.unit = None
            self.source_unit = None
            self.scale_factor = 1
            if column_values:
                values_width = max(
                    len(str(value if value is not None else ""))
                    for value in column_values
                )

        title_width = len(self.display_title or self.title)
        self.max_width = max(title_width, values_width)

    def __str__(self):
        return (
            f"{self.__class__.__name__}("
            f"title={self.title}, "
            f"pattern={self.pattern}, "
            f"num_of_digits={self.number_of_significant_digits}, "
            f"href={self.href}, "
            f"col_type={self.type}, "
            f"unit={self.unit}, "
            f"scale_factor={self.scale_factor})"
        )


def _format_number_align(formattedValue, max_number_of_dec_digits):
    with decimal.localcontext(DECIMAL_CONTEXT):
        alignment = max_number_of_dec_digits

        if formattedValue.find(".") >= 0:
            # Subtract spaces for digits after the decimal point.
            alignment -= len(formattedValue) - formattedValue.find(".") - 1
        elif max_number_of_dec_digits > 0:
            # Add punctuation space.
            formattedValue += "&#x2008;"

        return formattedValue + ("&#x2007;" * alignment)


def _get_significant_digits(value):
    with decimal.localcontext(DECIMAL_CONTEXT):

        if not Decimal(value).is_finite():
            return 0

        # Regular expression returns multiple groups:
        #
        # Group GROUP_SIGN: Optional sign of value
        # Group GROUP_INT_PART: Digits in front of decimal point
        # Group GROUP_DEC_PART: Optional decimal point and digits after it
        # Group GROUP_SIG_DEC_DIGITS: Digits after decimal point, starting at the first value not 0
        # Group GROUP_EXP: Optional exponent part (e.g. 'e-5')
        # Group GROUP_EXP_SIGN: Optional sign of exponent part
        # Group GROUP_EXP_VALUE: Value of exponent part (e.g. '5' for 'e-5')
        # Use these groups to compute the number of zeros that have to be added to the current number's
        # decimal positions.
        match = REGEX_MEASURE.match(value)
        assert match, "unexpected output format for number formatting"

        if int(match.group(GROUP_INT_PART)) == 0 and Decimal(value) != 0:
            sig_digits = len(match.group(GROUP_SIG_DEC_PART))

        else:
            if Decimal(value) != 0:
                sig_digits = len(match.group(GROUP_INT_PART))
            else:
                # If the value consists of only zeros, do not count the 0 in front of the decimal
                sig_digits = 0
            if match.group(GROUP_DEC_PART):
                sig_digits += (
                    len(match.group(GROUP_DEC_PART)) - 1
                )  # -1 for decimal point

        return sig_digits


def _format_number(
    number,
    initial_value_sig_digits,
    number_of_significant_digits,
    max_digits_after_decimal,
    format_target,
):
    """
    If the value is a number (or number followed by a unit),
    this function returns a string-representation of the number
    with the specified number of significant digits,
    optionally aligned at the decimal point.
    """
    with decimal.localcontext(DECIMAL_CONTEXT):

        assert format_target in POSSIBLE_FORMAT_TARGETS, (
            "Invalid format " + format_target
        )

        if number == 0:
            intended_digits = min(
                number_of_significant_digits, initial_value_sig_digits
            )
            # Add as many trailing zeros as desired
            rounded_value = Decimal(0).scaleb(-intended_digits)

        else:
            # Round to the given amount of significant digits
            intended_digits = min(
                initial_value_sig_digits, number_of_significant_digits
            )

            assert number.adjusted() == int(floor(abs(number).log10()))
            rounding_point = -number.adjusted() + (intended_digits - 1)
            # Contrary to its documentation, round() seems to be affected by the rounding
            # mode of decimal's context (which is good for us) when rounding Decimals.
            # We add an assertion to double check (calling round() is easier to understand).
            rounded_value = round(number, rounding_point)
            assert rounded_value == number.quantize(Decimal(1).scaleb(-rounding_point))

        formatted_value = print_decimal(rounded_value)

        # Get the number of resulting significant digits.
        current_sig_digits = _get_significant_digits(formatted_value)

        if current_sig_digits > intended_digits:
            if "." in formatted_value:
                # Happens when rounding 9.99 to 10 with 2 significant digits,
                # the formatted_value will be 10.0 and we need to cut one trailing zero.
                assert current_sig_digits == intended_digits + 1
                assert formatted_value.endswith("0")
                formatted_value = formatted_value[:-1].rstrip(".")
            else:
                # happens for cases like 12300 with 3 significant digits
                assert formatted_value == str(round(rounded_value))
        else:
            assert current_sig_digits == intended_digits

        # Cut the 0 in front of the decimal point for values < 1.
        # Example: 0.002 => .002
        if _is_to_cut(formatted_value, format_target):
            assert formatted_value.startswith("0.")
            formatted_value = formatted_value[1:]

        # Alignment
        if format_target == "html_cell":
            formatted_value = _format_number_align(
                formatted_value, max_digits_after_decimal
            )
        return formatted_value


def _is_to_cut(value, format_target):
    with decimal.localcontext(DECIMAL_CONTEXT):
        correct_target = format_target == "html_cell"
        return correct_target and "." in value and 1 > Decimal(value) >= 0


def _get_column_type_heur(
    column, column_values
) -> Union[  # noqa: TAE002 TODO should really be improved
    ColumnType,
    Tuple[Union[ColumnType, ColumnMeasureType], str, str, Union[int, Decimal], int],
]:
    with decimal.localcontext(DECIMAL_CONTEXT):
        if column.title == "status":
            return ColumnType.status

        column_type = column.type or None
        if column_type and column_type.type == ColumnType.measure:
            column_type = ColumnMeasureType(0)
        column_unit = column.unit  # May be None
        column_source_unit = column.source_unit  # May be None
        column_scale_factor = column.scale_factor  # May be None

        column_max_int_digits = 0
        column_max_dec_digits = 0
        column_has_numbers = False
        column_has_decimal_numbers = False

        if column_unit:
            explicit_unit_defined = True
        else:
            explicit_unit_defined = False

        if column_scale_factor is None:
            explicit_scale_defined = False
        else:
            explicit_scale_defined = True

        for value in column_values:
            if value is None or value == "":
                continue

            value_match = REGEX_MEASURE.match(str(value))

            # As soon as one row's value is no number, the column type is 'text'
            if value_match is None:
                return ColumnType.text
            else:
                column_has_numbers = True
                curr_column_unit = value_match.group(GROUP_UNIT)

                # If the units in two different rows of the same column differ,
                # 1. Raise an error if an explicit unit is defined by the displayUnit attribute
                #    and the unit in the column cell differs from the defined sourceUnit, or
                # 2. Handle the column as 'text' type, if no displayUnit was defined for the column's values.
                #    In that case, a unit different from the definition of sourceUnit does not lead to an error.
                if curr_column_unit:
                    if column_source_unit is None and not explicit_scale_defined:
                        column_source_unit = curr_column_unit
                    elif column_source_unit != curr_column_unit:
                        raise util.TableDefinitionError(
                            f"Attribute sourceUnit different from real source unit: "
                            f"{column_source_unit} and {curr_column_unit} (in column {column.title})"
                        )
                    if column_unit and curr_column_unit != column_unit:
                        if explicit_unit_defined:
                            _check_unit_consistency(
                                curr_column_unit, column_source_unit, column
                            )
                        else:
                            return ColumnType.text
                    else:
                        column_unit = curr_column_unit

                if column_scale_factor is None:
                    column_scale_factor = _get_scale_factor(
                        column_unit, column_source_unit, column
                    )

                # Compute the number of decimal digits of the current value, considering the number of significant
                # digits for this column.
                # Use the column's scale factor for computing the decimal digits of the current value.
                # Otherwise, they might be different from output.
                scaled_value = (
                    Decimal(util.remove_unit(str(value))) * column_scale_factor
                )

                # Due to the scaling operation above, floats in the exponent notation may be created. Since this creates
                # special cases, immediately convert the value back to decimal notation.
                if value_match.group(GROUP_DEC_PART):
                    # -1 since GROUP_DEC_PART includes the decimal point
                    dec_digits_before_scale = len(value_match.group(GROUP_DEC_PART)) - 1
                else:
                    dec_digits_before_scale = 0
                max_number_of_dec_digits_after_scale = max(
                    0, dec_digits_before_scale - ceil(log10(column_scale_factor))
                )

                scaled_value = (
                    f"{scaled_value:.{max_number_of_dec_digits_after_scale}f}"
                )
                scaled_value_match = REGEX_MEASURE.match(scaled_value)
                assert (
                    scaled_value_match
                ), "unexpected output format for number formatting"

                curr_dec_digits = _get_decimal_digits(
                    scaled_value_match, column.number_of_significant_digits
                )
                column_max_dec_digits = max(column_max_dec_digits, curr_dec_digits)

                curr_int_digits = _get_int_digits(scaled_value_match)
                column_max_int_digits = max(column_max_int_digits, curr_int_digits)

                if (
                    scaled_value_match.group(GROUP_DEC_PART) is not None
                    or value_match.group(GROUP_DEC_PART) is not None
                    or scaled_value_match.group(GROUP_SPECIAL_FLOATS_PART) is not None
                ):
                    column_has_decimal_numbers = True

        if not column_has_numbers:
            # only empty values
            return ColumnType.text

        if (
            column_has_decimal_numbers
            or column_max_dec_digits
            or int(column_scale_factor) != column_scale_factor  # non-int scaling factor
        ):
            column_type = ColumnMeasureType(column_max_dec_digits)
        else:
            column_type = ColumnType.count

        column_width = column_max_int_digits
        if column_max_dec_digits:
            column_width += column_max_dec_digits + 1

        return (
            column_type,
            column_unit,
            column_source_unit,
            column_scale_factor,
            column_width,
        )


# This function assumes that scale_factor is not defined.
# Because of this, an error is raised if unit is defined, different from the source_unit, and
# no conversion for these two units is known.
# (Since a scale_factor must be given explicitly, then)
def _get_scale_factor(unit, source_unit, column):
    if unit is None or unit == source_unit:
        return 1
    elif (
        source_unit in UNIT_CONVERSION.keys()
        and unit in UNIT_CONVERSION[source_unit].keys()
    ):
        return UNIT_CONVERSION[source_unit][unit]
    else:
        # If the display unit is different from the source unit, a scale factor must be given explicitly
        raise util.TableDefinitionError(
            "Attribute displayUnit is different from sourceUnit,"
            f" but scaleFactor is not defined (in column {column.title})"
        )


def _get_decimal_digits(decimal_number_match, number_of_significant_digits):
    """
    Returns the amount of decimal digits of the given regex match, considering the number of significant
    digits for the provided column.

    @param decimal_number_match: a regex match of a decimal number, resulting from REGEX_MEASURE.match(x).
    @param number_of_significant_digits: the number of significant digits required
    @return: the number of decimal digits of the given decimal number match's representation, after expanding
        the number to the required amount of significant digits
    """
    with decimal.localcontext(DECIMAL_CONTEXT):

        # check that only decimal notation is used
        assert "e" not in decimal_number_match.group()

        try:
            num_of_digits = int(number_of_significant_digits)
        except TypeError:
            num_of_digits = DEFAULT_NUMBER_OF_SIGNIFICANT_DIGITS

        if not decimal_number_match.group(GROUP_DEC_PART):
            return 0

        # If 1 > value > 0, only look at the decimal digits.
        # In the second condition, we have to remove the first character from the decimal part group because the
        # first character always is '.'
        if (
            int(decimal_number_match.group(GROUP_INT_PART)) == 0
            and int(decimal_number_match.group(GROUP_DEC_PART)[1:]) != 0
        ):
            max_num_of_digits = len(decimal_number_match.group(GROUP_SIG_DEC_PART))
            num_of_digits = min(num_of_digits, max_num_of_digits)
            # number of needed decimal digits = number of zeroes after decimal point + significant digits
            curr_dec_digits = len(decimal_number_match.group(GROUP_ZEROES)) + int(
                num_of_digits
            )

        else:
            max_num_of_digits = (
                len(decimal_number_match.group(GROUP_INT_PART))
                + len(decimal_number_match.group(GROUP_DEC_PART))
                - 1  # for decimal point, which is guaranteed to exist at this point
            )
            num_of_digits = min(num_of_digits, max_num_of_digits)
            # number of needed decimal digits = significant digits - number of digits in front of decimal point
            curr_dec_digits = int(num_of_digits) - len(
                decimal_number_match.group(GROUP_INT_PART)
            )

        return curr_dec_digits


def _get_int_digits(decimal_number_match):
    """
    Returns the amount of integer digits of the given regex match.
    @param number_of_significant_digits: the number of significant digits required
    """
    with decimal.localcontext(DECIMAL_CONTEXT):
        int_part = decimal_number_match.group(GROUP_INT_PART) or ""
        if int_part == "0":
            # we skip leading zeros of numbers < 1
            int_part = ""
        return len(int_part)


def _check_unit_consistency(actual_unit, wanted_unit, column):
    if actual_unit and wanted_unit is None:
        raise util.TableDefinitionError(
            f"Trying to convert from one unit to another, "
            f"but source unit not specified (in column {column.title})"
        )
    elif wanted_unit != actual_unit:
        raise util.TableDefinitionError(
            f"Source value of different unit than specified source unit: "
            f"{actual_unit} and {wanted_unit} (in column {column.title})"
        )
