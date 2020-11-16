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


class TaskId(collections.namedtuple("TaskId", "name property expected_result runset")):
    """Uniquely identifies a task (name of input file, property, etc.)."""

    field_names = ["Task name", "Property", "Expected verdict", "Run set"]

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
    if not is_url(path_or_url):
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


def is_url(path_or_url):
    return "://" in path_or_url or path_or_url.startswith("file:")


def to_decimal(s):
    if s:
        if s.lower() in ["nan", "inf", "-inf"]:
            return Decimal(s)
        else:
            # remove whitespaces and trailing units (e.g., in '1.23s')
            s, _ = split_number_and_unit(s.strip())
            return Decimal(s) if s else None
    else:
        return None


def print_decimal(d):
    """
    Print a Decimal instance in non-scientific (i.e., decimal) notation with full
    precision, i.e., all digits are printed exactly as stored in the Decimal instance.
    Note that str(d) always falls back to scientific notation for very small values.
    """

    if d.is_nan():
        return "NaN"
    elif d.is_infinite():
        return "Inf" if d > 0 else "-Inf"
    assert d.is_finite()

    sign, digits, exp = d.as_tuple()
    # sign is 1 if negative
    # digits is exactly the sequence of significant digits in the decimal representation
    # exp tells us whether we need to shift digits (pos: left shift; neg: right shift).
    # left shift can only add zeros, right shift adds decimal separator

    sign = "-" if sign == 1 else ""
    digits = list(map(str, digits))

    if exp >= 0:
        if digits == ["0"]:
            # special case: return "0" instead of "0000" for "0e4"
            return sign + "0"
        return sign + "".join(digits) + ("0" * exp)

    # Split digits into parts before and after decimal separator.
    # If -exp > len(digits) the result needs to start with "0.", so we force a 0.
    integral_part = digits[:exp] or ["0"]
    decimal_part = digits[exp:]
    assert decimal_part

    return (
        sign
        + "".join(integral_part)
        + "."
        + ("0" * (-exp - len(decimal_part)))  # additional zeros if necessary
        + "".join(decimal_part)
    )


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
