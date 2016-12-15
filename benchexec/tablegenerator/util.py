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

from benchexec import model


def get_file_list(shortFile):
    """
    The function get_file_list expands a short filename to a sorted list
    of filenames. The short filename can contain variables and wildcards.
    """
    if "://" in shortFile: # seems to be a URL
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
    '''
    This function takes a list of files, expands wildcards
    and returns a new list of files.
    '''
    return [file for wildcardFile in filelist for file in get_file_list(wildcardFile)]


def make_url(path_or_url):
    """Make a URL from a string which is either a URL or a local path,
    by adding "file:" if necessary.
    """
    if not "://" in path_or_url and not path_or_url.startswith("file:"):
        return "file:" + urllib.request.pathname2url(path_or_url)
    return path_or_url


def open_url_seekable(path_url, mode='rt'):
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
    if not s:
        return (s, '')
    pos = len(s)
    while pos and not s[pos-1].isdigit():
        pos -= 1
    return (s[:pos], s[pos:])


def remove_unit(s):
    """
    Remove a unit from a number string, or return the full string if it is not a number.
    """
    (prefix, suffix) = split_number_and_unit(s)
    return suffix if prefix == '' else prefix


def create_link(runResult, base_dir, column):
    source_file = runResult.task_id[0]
    href = column.href or runResult.log_file

    if href.startswith("http://") or href.startswith("https://") or href.startswith("file:"):
        # quote special characters only in inserted variable values, not full URL
        source_file = url_quote(source_file)
        href = model.substitute_vars([href], None, source_file)[0]
        return href

    # quote special characters everywhere (but not twice in source_file!)
    href = model.substitute_vars([href], None, source_file)[0]
    return url_quote(os.path.relpath(href, base_dir))


def format_options(options):
    '''Helper function for formatting the content of the options line'''
    # split on one of the following tokens: ' -' or '[[' or ']]'
    lines = ['']
    for token in re.split('( -|\[\[|\]\])', options):
        if token in ['[[',']]']:
            lines.append(token)
            lines.append('')
        elif token == ' -':
            lines.append(token)
        else:
            lines[-1] += token
    # join all non-empty lines and wrap them into 'span'-tags
    return '<span style="display:block">' + '</span><span style="display:block">'.join(line for line in lines if line.strip()) + '</span>'

def to_decimal(s):
    # remove whitespaces and trailing units (e.g., in '1.23s')
    if s:
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
    for column in sourcefileTag.findall('column'):
        if column.get('title') == columnTitle:
                return column.get('value')
    return default


def flatten(list_):
    return [value for sublist in list_ for value in sublist]


def to_json(obj):
    return tempita.html(json.dumps(obj, sort_keys=True))


def prettylist(list_):
    if not list_:
        return ''

    # Filter out duplicate values while keeping order
    values = set()
    uniqueList = []
    for entry in list_:
        if not entry in values:
            values.add(entry)
            uniqueList.append(entry)

    return uniqueList[0] if len(uniqueList) == 1 \
        else '[' + '; '.join(uniqueList) + ']'


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
