# BenchExec is a framework for reliable benchmarking.
# This file is part of BenchExec.
#
# Copyright (C) 2007-2015  Dirk Beyer
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

"""
This module contains some useful functions for Strings, Files and Lists.
"""

# prepare for Python 3
from __future__ import absolute_import, division, print_function, unicode_literals

from decimal import Decimal
import glob
import io
import json
import logging
import os
import re
from urllib.parse import quote as url_quote
import urllib.request
import tempita
import copy
from functools import reduce

import benchexec.util


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
    response = urllib.request.urlopen(path_url)
    logging.debug("Got response %s", response.info())

    try:
        response.seek(0)
    except (IOError, AttributeError):
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
        return (s, "")
    pos = len(s)
    while pos and numbers_into_suffix == s[pos - 1].isdigit():
        pos -= 1
    return (s[:pos], s[pos:])


def remove_unit(s):
    """
    Remove a unit from a number string, or return the full string if it is not a number.
    """
    (prefix, suffix) = split_number_and_unit(s)
    return suffix if prefix == "" else prefix


def is_url(path_or_url):
    return "://" in path_or_url or path_or_url.startswith("file:")


def create_link(href, base_dir, runResult=None, href_base=None):
    def get_replacements(source_file):
        return (
            [
                ("inputfile_name", os.path.basename(source_file)),
                ("inputfile_path", os.path.dirname(source_file) or "."),
                ("inputfile_path_abs", os.path.dirname(os.path.abspath(source_file))),
                # The following are deprecated: do not use anymore.
                ("sourcefile_name", os.path.basename(source_file)),
                ("sourcefile_path", os.path.dirname(source_file) or "."),
                ("sourcefile_path_abs", os.path.dirname(os.path.abspath(source_file))),
            ]
            + (
                [
                    ("taskdef_name", os.path.basename(source_file)),
                    ("taskdef_path", os.path.dirname(source_file) or "."),
                    ("taskdef_path_abs", os.path.dirname(os.path.abspath(source_file))),
                ]
                if source_file.endswith(".yml")
                else []
            )
            + (
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
        )

    source_file = (
        os.path.relpath(runResult.task_id[0], href_base or ".") if runResult else None
    )

    if is_url(href):
        # quote special characters only in inserted variable values, not full URL
        if source_file:
            source_file = url_quote(source_file)
            href = benchexec.util.substitute_vars(href, get_replacements(source_file))
        return href

    # quote special characters everywhere (but not twice in source_file!)
    if source_file:
        href = benchexec.util.substitute_vars(href, get_replacements(source_file))
    return url_quote(os.path.relpath(href, base_dir))


def format_options(options):
    """Helper function for formatting the content of the options line"""
    # split on one of the following tokens: ' -' or '[[' or ']]'
    lines = [""]
    for token in re.split(r"( -|\[\[|\]\])", options):
        if token in ["[[", "]]"]:
            lines.append(token)
            lines.append("")
        elif token == " -":
            lines.append(token)
        else:
            lines[-1] += token
    # join all non-empty lines and wrap them into 'span'-tags
    return (
        '<span style="display:block">'
        + '</span><span style="display:block">'.join(
            line for line in lines if line.strip()
        )
        + "</span>"
    )


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

# parse -> cases: to big numbers / Key-Value / List
def to_json(obj):
    # return tempita.html(json.dumps(obj, sort_keys=True))
    return tempita.html(json.dumps(obj, sort_keys=True, default=parse_json))

def parse_json(obj):
    if type(obj) is Decimal: # for decimal numbers
        return float(obj)
    elif "__dict__" in dir(obj): # e.g. for own Classes (Key-value)
        # wenn die <Funktionen eines dictionaries> in dem object vorkommen, dann behandel es wie ein dictionary
        return obj.__dict__
    elif "__iter__" in dir(obj): # e.g. for Set (List)
        return list(obj)
    else:
        obj

def merge_dicts(*dicts):
    return dict(reduce(lambda acc,cur: acc + list(cur.items()), dicts, []))

def prepare_run_sets_for_js(run_sets, columns):
    # javascript pendant:
    # // var tools = run_sets.map((rs, i) => {
    # //   return { ...rs, columns: columns_data[i] }
    # // })
    return [merge_dicts(rs, {'columns': columns[i]}) for i, rs in enumerate(run_sets)] #Tupel (index + column)

def prepare_rows_for_js(rows, tools, base_dir, href_base):
    row_exclude_keys = {'properties'}
    results_exclude_keys = {'columns', 'task_id', 'sourcefiles_exist', 'status'}

    def prepare_values(column, value):
        return {
            'original': column.format_value(value, False, 'html_cell'),
            'formatted': column.format_value(value, True, 'html_cell'),
        }

    def clean_up_results(res, i):
        values = [prepare_values(column, res.values[i]) for i, column in enumerate(res.columns)]
        toolHref = [column.href for column in tools[i]['columns'] if column.title.endswith('status')][0]
        href = create_link(toolHref or res.log_file, base_dir, res, href_base)
        return merge_dicts({'href': href, 'values': values}, {k: v for k, v in res.__dict__.items() if k not in results_exclude_keys})

    def clean_up_row(row):
        #(if key not in exclude) {res.__dict__.items.map((k, v) => {
        #    k: v (= key: value)
        #})}
        row = {k: v for k, v in row.__dict__.items() if k not in row_exclude_keys} 
        row['results'] = [clean_up_results(res, i) for i, res in enumerate(row['results'])]
        row['href'] = create_link(row['filename'], base_dir)
        return row

    return [clean_up_row(row) for row in copy.deepcopy(rows)]

def prepare_stats_for_js(stats, tools):
    toolColumnCounts = [len(tool["columns"]) for tool in tools] #len === .length() => [9, 4, 6]

    def prepare_values(column, value, key):
        return column.format_value(value, True, 'html_cell') if key is 'sum' else column.format_value(value, False, 'tooltip')

    def get_stat_content(stat, i, count):
        start = reduce(lambda acc, cur: acc + cur, toolColumnCounts[0:i], 0)
        return stat.content[start:start+count]  #reduce(labda acc, cur: acc + curr) 

    def clean_up_stat(stat):
        content_splitted = [get_stat_content(stat, i, count) for (i, count) in enumerate(toolColumnCounts)]
        return [[{k: prepare_values(tools[toolIndex]['columns'][colIndex], v, k) for k, v in content.__dict__.items()} for colIndex, content in enumerate(toolContent) if content is not None] for toolIndex, toolContent in enumerate(content_splitted)]

    return [merge_dicts(stat, {"content": clean_up_stat(stat)}) for stat in copy.deepcopy(stats)] # add original stat infos
    # return [[[{k: prepare_values(tools[toolIndex]['columns'][colIndex], v, k) for k, v in content.__dict__.items()} for colIndex, content in enumerate(toolContent) if content is not None] for toolIndex, toolContent in enumerate(stat['content'])] for stat in stats_prepared]

def read_frontend_asset(file_name, format):
    return open(file_name.format(format=format), "r").read()

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
        if not entry in values:
            values.add(entry)
            uniqueList.append(entry)

    return uniqueList[0] if len(uniqueList) == 1 else "[" + "; ".join(uniqueList) + "]"


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
