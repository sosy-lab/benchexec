# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

"""
This module contains some useful functions for Strings, Files and Lists.
"""

import collections
from decimal import Decimal
import glob
import io
import logging
import os
import urllib.request
import platform
from typing import Iterable, List, TypeVar, Union

import benchexec.util


# May be extended with higher numbers
ROMAN_NUMBERS = {
    1000: "M",
    500: "D",
    100: "C",
    50: "L",
    10: "X",
    5: "V",
    1: "I",
}

_T = TypeVar("_T")


class TaskId(
    collections.namedtuple(
        "TaskId", "name property expected_result witness_category runset"
    )
):
    """Uniquely identifies a task (name of input file, property, etc.)."""

    field_names = [
        "Task name",
        "Property",
        "Expected verdict",
        "Witness category",
        "Run set",
    ]

    __slots__ = ()  # reduce per-instance memory consumption

    def __str__(self):
        return "'" + ", ".join(str(s) for s in self if s) + "'"


def get_file_list(shortFile):
    """
    The function get_file_list expands a short filename to a sorted list
    of filenames. The short filename can contain variables and wildcards.
    """
    if "://" in shortFile:  # seems to be a URL
        return [shortFile]

    # expand tilde and variables
    expandedFile = os.path.expandvars(os.path.expanduser(shortFile))

    # expand wildcards
    fileList = glob.glob(expandedFile)

    # sort alphabetical,
    # if list is emtpy, sorting returns None, so better do not sort
    if len(fileList) != 0:
        fileList.sort()
    else:
        logging.warning("No file matches '%s'.", shortFile)

    return fileList


def extend_file_list(filelist):
    """
    This function takes a list of files, expands wildcards
    and returns a new list of files.
    """
    return [file for wildcardFile in filelist for file in get_file_list(wildcardFile)]


def make_url(path_or_url):
    """Make a URL from a string which is either a URL or a local path,
    by adding "file:" if necessary.
    """
    if not benchexec.util.is_url(path_or_url):
        return "file:" + urllib.request.pathname2url(path_or_url)
    return path_or_url


def open_url_seekable(path_url, mode="rt"):
    """Open a URL and ensure that the result is seekable,
    copying it into a buffer if necessary."""

    logging.debug("Making request to '%s'", path_url)
    response = urllib.request.urlopen(path_url)  # noqa: S310
    logging.debug("Got response %s", response.info())

    try:
        response.seek(0)
    except (OSError, AttributeError):
        # Copy into buffer to allow seeking.
        response = io.BytesIO(response.read())
    if "b" in mode:
        return response
    else:
        return io.TextIOWrapper(response)


def split_number_and_unit(s):
    """
    Split a string into two parts: a number prefix and an arbitrary suffix.
    Splitting is done from the end, so the split is where the last digit
    in the string is (that means the prefix may include non-digit characters,
    if they are followed by at least one digit).
    """
    return split_string_at_suffix(s, False)


def split_string_at_suffix(s, numbers_into_suffix=False):
    """
    Split a string into two parts: a prefix and a suffix. Splitting is done from the end,
    so the split is done around the position of the last digit in the string
    (that means the prefix may include any character, mixing digits and chars).
    The flag 'numbers_into_suffix' determines whether the suffix consists of digits or non-digits.
    """
    if not s:
        return s, ""
    pos = len(s)
    while pos and numbers_into_suffix == s[pos - 1].isdigit():
        pos -= 1
    return s[:pos], s[pos:]


def remove_unit(s):
    """
    Remove a unit from a number string, or return the full string if it is not a number.
    """
    (prefix, suffix) = split_number_and_unit(s)
    return suffix if prefix == "" else prefix


def to_decimal(s):
    if s is None:
        return None
    if isinstance(s, str):
        s = s.strip()
        if s.lower() in ["nan", "inf", "+inf", "-inf"]:
            return Decimal(s)
        else:
            # remove trailing units (e.g., in '1.23s')
            s, _ = split_number_and_unit(s)
            return Decimal(s) if s else None
    else:
        return Decimal(s)


def collapse_equal_values(values, counts):
    """
    Take a tuple (values, counts), remove consecutive values and increment their count instead.
    """
    assert len(values) == len(counts)
    previousValue = values[0]
    previousCount = 0

    for value, count in zip(values, counts):
        if value != previousValue:
            yield (previousValue, previousCount)
            previousCount = 0
            previousValue = value
        previousCount += count

    yield (previousValue, previousCount)


def get_column_value(sourcefileTag, columnTitle, default=None):
    for column in sourcefileTag.findall("column"):
        if column.get("title") == columnTitle:
            return column.get("value")
    return default


def flatten(list_):
    return [value for sublist in list_ for value in sublist]


def merge_entries_with_common_prefixes(list_, number_of_needed_commons=6):
    """
    Returns a list where sequences of post-fixed entries are shortened to their common prefix.
    This might be useful in cases of several similar values,
    where the prefix is identical for several entries.
    If less than 'number_of_needed_commons' are identically prefixed, they are kept unchanged.
    Example: ['test', 'pc1', 'pc2', 'pc3', ... , 'pc10'] -> ['test', 'pc*']
    """
    # first find common entry-sequences
    prefix = None
    lists_to_merge = []
    for entry in list_:
        newPrefix, number = split_string_at_suffix(entry, numbers_into_suffix=True)
        if entry == newPrefix or prefix != newPrefix:
            lists_to_merge.append([])
            prefix = newPrefix
        lists_to_merge[-1].append((entry, newPrefix, number))

    # then merge them
    returnvalue = []
    for common_entries in lists_to_merge:
        common_prefix = common_entries[0][1]
        assert all(common_prefix == prefix for entry, prefix, number in common_entries)
        if len(common_entries) <= number_of_needed_commons:
            returnvalue.extend((entry for entry, prefix, number in common_entries))
        else:
            # we use '*' to indicate several entries,
            # it would also be possible to use '[min,max]' from '(n for e,p,n in common_entries)'
            returnvalue.append(common_prefix + "*")

    return returnvalue


def prettylist(list_):
    """
    Filter out duplicate values while keeping order.
    """
    if not list_:
        return ""

    values = set()
    uniqueList = []

    for entry in list_:
        if entry not in values:
            values.add(entry)
            uniqueList.append(entry)

    return uniqueList[0] if len(uniqueList) == 1 else "[" + "; ".join(uniqueList) + "]"


def merge_lists(list_of_lists: Iterable[Iterable[_T]]) -> List[_T]:
    """
    This function merges several sequences, e.g. [A,C] + [A,B] --> [A,B,C].
    It keeps the order of elements.
    """
    result_list = []
    elem_set = set()
    for current_list in list_of_lists:
        # prev_index is for optimizing inserting consecutive sequences of new elems,
        # e.g., in the first outer loop iteration.
        prev_index = None
        # In later iterations of the outer loop, it can happen that we see [a,b] where
        # a already exists at some place in result_list and b does not.
        # Then we want to insert b right after a, so we need to remember a and find it.
        prev_elem = None
        for elem in current_list:
            if elem not in elem_set:
                elem_set.add(elem)
                # calculate where to insert in result_list
                if prev_index is not None:
                    index = prev_index + 1
                elif prev_elem is not None:
                    index = result_list.index(prev_elem) + 1
                else:
                    index = 0
                result_list.insert(index, elem)
                prev_index = index
                prev_elem = elem
            else:
                prev_index = None
                prev_elem = elem

    return result_list


def find_common_elements(sequences: Iterable[Iterable[_T]]) -> List[_T]:
    """Return the common elements in some sequences (keeping order)."""
    # We take care to iterate sequences and all its elements only once
    # such that it works with generators as well and is efficient.
    sequences = iter(sequences)
    elems_in_first_list = list(next(sequences))

    elem_set = set(elems_in_first_list)
    elem_set.intersection_update(*sequences)

    if not elem_set:
        return []
    elif len(elems_in_first_list) == len(elem_set):
        return elems_in_first_list
    else:
        return [elem for elem in elems_in_first_list if elem in elem_set]


def read_bundled_file(name):
    """Read a file that is packaged together with this application."""
    try:
        return __loader__.get_data(name).decode("UTF-8")  # pytype: disable=name-error
    except NameError:
        with open(name, mode="r") as f:
            return f.read()


def fix_path_if_on_windows(path):
    return path if platform.system() != "Windows" else path.replace("\\", "/")


def normalize_line_endings(text):
    return text.replace("\r\n", "\n")


def number_to_roman_string(number: Union[int, str]) -> str:
    """Converts a positive number into the roman form.

    For example:
    3 -> III
    14 -> XIV

    Useful for Latex command generation

    Args:
        number: An integer or string

    Returns:
        A string which represents the given number in roman number format.
    """

    number = int(number)
    if number < 1:
        raise ValueError(
            "%s not positive. Only positive numbers can be converted to roman number format",
            number,
        )

    max_number = max(ROMAN_NUMBERS)
    # Count specifies how often max_number fits into number
    # Number will be the remainder after the divmod (e.g. number < max_number after divmod)
    count, number = divmod(number, max_number)
    output_string = ROMAN_NUMBERS[max_number] * count

    highest_power = 1
    while highest_power <= number:
        highest_power *= 10
    highest_power /= 10

    # Displaying each "digit" (with zeros) in roman number format. For example number = 933:
    # Start with 900 -> CM, then subtract 900 from 933.
    # Now convert 30 -> XXX, subtract it from 33 and append it to output_string (CM + XXX = CMXXX).
    # Last convert 3 -> III and subtract it from 3 and append it to output_string (CMXXXIII).
    while number > 0:
        if number >= highest_power:
            prefix = int(number / highest_power)
            number -= prefix * highest_power

            if prefix <= 3:  # Fill with current letter
                output_string += ROMAN_NUMBERS[highest_power] * prefix
            elif prefix == 4:  # Take higher letter and use current letter before
                output_string += (
                    ROMAN_NUMBERS[highest_power] + ROMAN_NUMBERS[highest_power * 5]
                )
            elif prefix <= 8:  # Higher letter and current letter afterwards
                output_string += ROMAN_NUMBERS[highest_power * 5] + ROMAN_NUMBERS[
                    highest_power
                ] * (prefix - 5)
            elif prefix == 9:  # Two times higher letter and current letter before
                output_string += (
                    ROMAN_NUMBERS[highest_power] + ROMAN_NUMBERS[highest_power * 10]
                )
            else:
                raise ValueError("Unexpected prefix %s", prefix)
        else:
            highest_power /= 10

    return output_string


def cap_first_letter(word: str) -> str:
    """Capitalizes the first letter in the given word, ignores the remaining letters

    This differs to pythons str.title() method. str.title() capitalizes the first letter and the remaining letters in lowercase.
    This method ignores the remaining letters.
    """
    if word:
        return word[0].capitalize() + word[1:]
    return ""


class _DummyFuture(object):
    def __init__(self, result):
        self._result = result

    def result(self):
        return self._result


class DummyExecutor(object):
    """Executor similar to concurrent.futures.ProcessPoolExecutor
    but executes everything sequentially in the current process.
    This can be useful for debugging.
    Not all features of ProcessPoolExecutor are supported.
    """

    def submit(self, func, *args, **kwargs):
        return _DummyFuture(func(*args, **kwargs))

    map = map

    def shutdown(self, wait=None):
        pass


class TableDefinitionError(Exception):
    """Exception raised for errors in the table definition.

    :param message Error message
    """

    def __init__(self, message):
        self.message = message
