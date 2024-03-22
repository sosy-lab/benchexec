# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import argparse
import bz2
import collections
import copy
import functools
import gzip
import io
import itertools
import logging
import os.path
import platform
import re
import signal
import subprocess
import sys
import time
import types
import typing
from typing import Iterator, List, Optional, Set
import urllib.parse
import urllib.request
from xml.etree import ElementTree

from benchexec import __version__, BenchExecException
import benchexec.model as model
import benchexec.result as result
import benchexec.tooladapter as tooladapter
import benchexec.util
from benchexec.tablegenerator import htmltable, statistics, util, statisticstex
from benchexec.tablegenerator.columns import Column
from benchexec.tablegenerator.util import TaskId
import zipfile

# Process pool for parallel work.
# Some of our loops are CPU-bound (e.g., statistics calculations), thus we use
# processes, not threads.
# Fully initialized only in main() because we cannot do so in the worker processes.
parallel = util.DummyExecutor()

# Most important columns that should be shown first in tables (in the given order)
MAIN_COLUMNS = [
    Column("status"),
    Column("category"),
    Column("cputime"),
    Column("walltime"),
    Column("memory", unit="MB", source_unit="B"),
    Column(
        "memUsage", display_title="memory", unit="MB", source_unit="B"
    ),  # if old results are given
    Column("cpuenergy"),
]

NAME_START = "results"  # first part of filename of table

DEFAULT_OUTPUT_PATH = "results"

# All available formats
TEMPLATE_FORMATS = ["html", "csv", "statistics-tex"]

# Default formats, if no format is specified
DEFAULT_TEMPLATE_FORMATS = ["html", "csv"]

_BYTE_FACTOR = 1000  # bytes in a kilobyte

UNIT_CONVERSION = {
    "s": {"ms": 1000, "min": 1.0 / 60, "h": 1.0 / 3600},
    "B": {"kB": 1.0 / 10**3, "MB": 1.0 / 10**6, "GB": 1.0 / 10**9},
    "J": {
        "kJ": 1.0 / 10**3,
        "Ws": 1,
        "kWs": 1.0 / 1000,
        "Wh": 1.0 / 3600,
        "kWh": 1.0 / (1000 * 3600),
        "mWh": 1.0 / (1000 * 1000 * 3600),
    },
}


def handle_error(message, *args):
    """Log error message and terminate program."""
    logging.error(message, *args)
    exit(1)


def parse_table_definition_file(file):
    """
    Read an parse the XML of a table-definition file.
    @return: an ElementTree object for the table definition
    """
    logging.info("Reading table definition from '%s'...", file)
    if not os.path.isfile(file):
        handle_error("File '%s' does not exist.", file)

    try:
        tableGenFile = ElementTree.ElementTree().parse(file)
    except OSError as e:
        handle_error("Could not read result file %s: %s", file, e)
    except ElementTree.ParseError as e:
        handle_error("Table file %s is invalid: %s", file, e)
    if "table" != tableGenFile.tag:
        handle_error(
            "Table file %s is invalid: It's root element is not named 'table'.", file
        )
    return tableGenFile


def table_definition_lists_result_files(table_definition):
    return any(tag.tag in ["result", "union"] for tag in table_definition)


def load_results_from_table_definition(
    table_definition, table_definition_file, options
) -> "Iterator[Optional[RunSetResult]]":
    """
    Load all results in files that are listed in the given table-definition file.
    @return: a list of RunSetResult objects
    """
    default_columns = extract_columns_from_table_definition_file(
        table_definition, table_definition_file
    )
    columns_relevant_for_diff = _get_columns_relevant_for_diff(default_columns)

    results = []
    for tag in table_definition:
        if tag.tag == "result":
            columns = (
                extract_columns_from_table_definition_file(tag, table_definition_file)
                or default_columns
            )
            run_set_id = tag.get("id")
            for resultsFile in get_file_list_from_result_tag(
                tag, table_definition_file
            ):
                results.append(
                    parallel.submit(
                        load_result,
                        resultsFile,
                        options,
                        run_set_id,
                        columns,
                        columns_relevant_for_diff,
                    )
                )

        elif tag.tag == "union":
            results.append(
                parallel.submit(
                    handle_union_tag,
                    tag,
                    table_definition_file,
                    options,
                    default_columns,
                    columns_relevant_for_diff,
                )
            )

    return (future.result() for future in results)


def handle_union_tag(
    tag, table_definition_file, options, default_columns, columns_relevant_for_diff
) -> "Optional[RunSetResult]":
    columns = (
        extract_columns_from_table_definition_file(tag, table_definition_file)
        or default_columns
    )
    result = RunSetResult([], collections.defaultdict(list), columns)
    all_result_files = set()

    for resultTag in tag.findall("result"):
        if extract_columns_from_table_definition_file(resultTag, table_definition_file):
            logging.warning(
                "<result> tags within <union> tags may not contain <column> tags, "
                "these column declarations will be ignored. Please move them to the <union> tag."
            )
        run_set_id = resultTag.get("id")
        for resultsFile in get_file_list_from_result_tag(
            resultTag, table_definition_file
        ):
            if resultsFile in all_result_files:
                handle_error("File '%s' included twice in <union> tag", resultsFile)
            all_result_files.add(resultsFile)
            result_xml = parse_results_file(resultsFile, run_set_id)
            if result_xml is not None:
                result.append(resultsFile, result_xml, options.all_columns)

    if not result._xml_results:
        return None

    name = tag.get("name")
    if name:
        logging.warning(
            "Attribute 'name' for <union> tags is deprecated, use 'title' instead."
        )
    name = tag.get("title", name)
    if name:
        result.attributes["name"] = [name]
    result.collect_data(options.correct_only)
    return result


def get_file_list_from_result_tag(result_tag, table_definition_file):
    if "filename" not in result_tag.attrib:
        logging.warning(
            "Result tag without filename attribute in file '%s'.", table_definition_file
        )
        return []
    # expand wildcards
    return util.get_file_list(
        os.path.join(os.path.dirname(table_definition_file), result_tag.get("filename"))
    )


def load_results_with_table_definition(
    result_files, table_definition, table_definition_file, options
) -> "Iterator[Optional[RunSetResult]]":
    """
    Load results from given files with column definitions taken from a table-definition file.
    @return: a list of RunSetResult objects
    """
    columns = extract_columns_from_table_definition_file(
        table_definition, table_definition_file
    )
    columns_relevant_for_diff = _get_columns_relevant_for_diff(columns)

    return load_results(
        result_files,
        options=options,
        columns=columns,
        columns_relevant_for_diff=columns_relevant_for_diff,
    )


def extract_columns_from_table_definition_file(xmltag, table_definition_file):
    """
    Extract all columns mentioned in the result tag of a table definition file.
    """

    def handle_path(path):
        """Convert path from a path relative to table-definition file."""
        if not path or path.startswith("http://") or path.startswith("https://"):
            return path
        return os.path.join(os.path.dirname(table_definition_file), path)

    columns = []
    for c in xmltag.findall("column"):
        scale_factor = c.get("scaleFactor")
        display_unit = c.get("displayUnit")
        source_unit = c.get("sourceUnit")

        new_column = Column(
            c.get("title"),
            c.text,
            c.get("numberOfDigits"),
            handle_path(c.get("href")),
            None,
            display_unit,
            source_unit,
            scale_factor,
            c.get("relevantForDiff"),
            c.get("displayTitle"),
        )
        columns.append(new_column)

    return columns


def _get_columns_relevant_for_diff(columns_to_show):
    """
    Extract columns that are relevant for the diff table.

    @param columns_to_show: (list) A list of columns that should be shown
    @return: (set) Set of columns that are relevant for the diff table. If
             none is marked relevant, the column named "status" will be
             returned in the set.
    """
    cols = {col.title for col in columns_to_show if col.relevant_for_diff}
    if len(cols) == 0:
        return {col.title for col in columns_to_show if col.title == "status"}
    else:
        return cols


def normalize_path(path, base_path_or_url):
    """Returns a normalized form of path, interpreted relative to base_path_or_url"""
    if benchexec.util.is_url(base_path_or_url):
        return urllib.parse.urljoin(base_path_or_url, path)
    else:
        return os.path.normpath(os.path.join(os.path.dirname(base_path_or_url), path))


loaded_tools = {}


def load_tool(result):
    """
    Load the module with the tool-specific code.
    """

    def load_tool_module(tool_module):
        if not tool_module:
            logging.warning(
                "Cannot extract values from log files for benchmark results %s "
                '(missing attribute "toolmodule" on tag "result").',
                util.prettylist(result.attributes["name"]),
            )
            return None
        try:
            logging.debug("Loading %s", tool_module)
            tool = __import__(tool_module, fromlist=["Tool"]).Tool()
            return tooladapter.adapt_to_current_version(tool)
        except ImportError as ie:
            logging.warning(
                'Missing module "%s", cannot extract values from log files (ImportError: %s).',
                tool_module,
                ie,
            )
        except AttributeError:
            logging.warning(
                'The module "%s" does not define the necessary class Tool, '
                "cannot extract values from log files.",
                tool_module,
            )
        except TypeError as te:
            logging.warning(
                'Unsupported module "%s", cannot extract values from log files '
                "(TypeError: %s).",
                tool_module,
                te,
            )
        return None

    tool_module = (
        result.attributes["toolmodule"][0]
        if "toolmodule" in result.attributes
        else None
    )
    if tool_module in loaded_tools:
        return loaded_tools[tool_module]
    else:
        loaded_tool = load_tool_module(tool_module)
        loaded_tools[tool_module] = loaded_tool
        return loaded_tool


class RunSetResult(object):
    """
    The Class RunSetResult contains all the results of one execution of a run set:
    the sourcefiles tags (with sourcefiles + values), the columns to show
    and the benchmark attributes.
    """

    def __init__(
        self,
        xml_results,
        attributes,
        columns,
        summary={},
        columns_relevant_for_diff=set(),
    ):
        self._xml_results = xml_results
        self.attributes = attributes
        # Copy the columns since they may be modified
        self.columns: List[Column] = copy.deepcopy(columns)
        self.summary = summary
        self.columns_relevant_for_diff: Set[str] = columns_relevant_for_diff
        self.results: List[RunResult]

    def get_tasks(self) -> Iterator[TaskId]:
        """
        Return the sequence of task ids for these results. This is free of duplicates.
        May be called only after collect_data()
        """
        return (r.task_id for r in self.results)

    def append(self, resultFile, resultElem, all_columns=False):
        """
        Append the result for one run. Needs to be called before collect_data().
        """
        self._xml_results += [
            (result, resultFile) for result in _get_run_tags_from_xml(resultElem)
        ]
        for attrib, values in RunSetResult._extract_attributes_from_result(
            resultFile, resultElem
        ).items():
            self.attributes[attrib].extend(values)

        if not self.columns:
            self.columns = RunSetResult._extract_existing_columns_from_result(
                resultFile, resultElem, all_columns
            )

    def collect_data(self, correct_only):
        """
        Load the actual result values from the XML file and the log files.
        This may take some time if many log files have to be opened and parsed.
        """
        self.results = []

        tool = load_tool(self)
        if tool:
            self.attributes["project_url"] = [tool.project_url()]

            versions = self.attributes["version"]
            if len(versions) == 1 and versions[0]:
                self.attributes["version_url"] = [tool.url_for_version(versions[0])]

        def get_value_from_logfile(lines, identifier):
            """
            This method searches for values in lines of the content.
            It uses a tool-specific method to so.
            """
            if not tool:
                return None
            output = tooladapter.CURRENT_BASETOOL.RunOutput(lines)
            return tool.get_value_from_output(output, identifier)

        # Opening the ZIP archive with the logs for every run is too slow, we cache it.
        log_zip_cache = {}
        task_set = set()
        try:
            for xml_result, result_file in self._xml_results:
                run_result = RunResult.create_from_xml(
                    xml_result,
                    get_value_from_logfile,
                    self.columns,
                    correct_only,
                    log_zip_cache,
                    self.columns_relevant_for_diff,
                    result_file,
                )
                task = run_result.task_id
                # Make sure to keep results free of duplicates
                if task in task_set:
                    logging.warning(
                        "Task %s is present twice in '%s', skipping it.", task, self
                    )
                else:
                    self.results.append(run_result)
                    task_set.add(task)
        finally:
            for file in log_zip_cache.values():
                file.close()

        for column in self.columns:
            column_values = (
                run_result.values[run_result.columns.index(column)]
                for run_result in self.results
            )
            column.set_column_type_from(column_values)

        del self._xml_results

    def __str__(self):
        return util.prettylist(self.attributes["filename"])

    @staticmethod
    def create_from_xml(
        resultFile,
        resultElem,
        columns=None,
        all_columns=False,
        columns_relevant_for_diff=set(),
    ):
        """
        This function extracts everything necessary for creating a RunSetResult object
        from the "result" XML tag of a benchmark result file.
        It returns a RunSetResult object, which is not yet fully initialized.
        To finish initializing the object, call collect_data()
        before using it for anything else
        (this is to separate the possibly costly collect_data() call from object instantiation).
        """
        attributes = RunSetResult._extract_attributes_from_result(
            resultFile, resultElem
        )

        if not columns:
            columns = RunSetResult._extract_existing_columns_from_result(
                resultFile, resultElem, all_columns
            )

        summary = RunSetResult._extract_summary_from_result(resultElem, columns)

        return RunSetResult(
            [(result, resultFile) for result in _get_run_tags_from_xml(resultElem)],
            attributes,
            columns,
            summary,
            columns_relevant_for_diff,
        )

    @staticmethod
    def _extract_existing_columns_from_result(resultFile, resultElem, all_columns):
        run_results = _get_run_tags_from_xml(resultElem)
        if not run_results:
            logging.warning("Result file '%s' is empty.", resultFile)
            # completely empty results break stuff, add at least status column
            return [MAIN_COLUMNS[0]]
        else:  # show all available columns
            column_names = {
                c.get("title")
                for s in run_results
                for c in s.findall("column")
                if all_columns or c.get("hidden") != "true"
            }

            if not column_names:
                # completely empty results break stuff, add at least status column
                return [MAIN_COLUMNS[0]]

            # Put main columns first, then rest sorted alphabetically
            custom_columns = column_names.difference(
                column.title for column in MAIN_COLUMNS
            )
            return [
                column for column in MAIN_COLUMNS if column.title in column_names
            ] + [Column(title) for title in sorted(custom_columns)]

    @staticmethod
    def _extract_attributes_from_result(resultFile, resultTag):
        attributes = collections.defaultdict(list)

        # Defaults
        attributes["filename"] = [resultFile]
        attributes["branch"] = [
            os.path.basename(resultFile).split("#")[0] if "#" in resultFile else ""
        ]
        attributes["timelimit"] = ["-"]
        attributes["memlimit"] = ["-"]
        attributes["cpuCores"] = ["-"]
        attributes["displayName"] = []

        # Update with real values
        for attrib, value in resultTag.attrib.items():
            attributes[attrib] = [value]

        # Add system information if present
        for systemTag in sorted(
            resultTag.findall("systeminfo"),
            key=lambda system_tag: system_tag.get("hostname", "unknown"),
        ):
            cpuTag = systemTag.find("cpu")
            attributes["os"].append(systemTag.find("os").get("name"))
            attributes["cpu"].append(cpuTag.get("model"))
            attributes["cores"].append(cpuTag.get("cores"))
            attributes["freq"].append(cpuTag.get("frequency"))
            attributes["turbo"].append(cpuTag.get("turboboostActive"))
            attributes["ram"].append(systemTag.find("ram").get("size"))
            attributes["host"].append(systemTag.get("hostname", "unknown"))

        return attributes

    @staticmethod
    def _extract_summary_from_result(resultTag, columns):
        summary = collections.defaultdict(list)

        # Add summary for columns if present
        for column in resultTag.findall("column"):
            title = column.get("title")
            if title in (c.title for c in columns):
                summary[title] = column.get("value")

        return summary


def _get_run_tags_from_xml(result_elem):
    # Here we keep support for <sourcefile> in order to be able to read old benchmark
    # results (no reason to forbid this).
    return result_elem.findall("run") + result_elem.findall("sourcefile")


def load_results(
    result_files,
    options,
    run_set_id=None,
    columns=None,
    columns_relevant_for_diff=set(),
) -> "Iterator[Optional[RunSetResult]]":
    """Version of load_result for multiple input files that will be loaded concurrently."""
    return parallel.map(
        load_result,
        result_files,
        itertools.repeat(options),
        itertools.repeat(run_set_id),
        itertools.repeat(columns),
        itertools.repeat(columns_relevant_for_diff),
    )


def load_result(
    result_file, options, run_set_id=None, columns=None, columns_relevant_for_diff=set()
) -> "Optional[RunSetResult]":
    """
    Completely handle loading a single result file.
    @param result_file the file to parse
    @param options additional options
    @param run_set_id the identifier of the run set
    @param columns the list of columns
    @param columns_relevant_for_diff a set of columns that is relevant for
                                     the diff table
    @return a fully ready RunSetResult instance or None
    """
    xml = parse_results_file(
        result_file, run_set_id=run_set_id, ignore_errors=options.ignore_errors
    )
    if xml is None:
        return None

    result = RunSetResult.create_from_xml(
        result_file,
        xml,
        columns=columns,
        all_columns=options.all_columns,
        columns_relevant_for_diff=columns_relevant_for_diff,
    )
    result.collect_data(options.correct_only)
    return result


def parse_results_file(resultFile, run_set_id=None, ignore_errors=False):
    """
    This function parses an XML file that contains the results of the execution of a run set.
    It returns the "result" XML tag.
    @param resultFile: The file name of the XML file that contains the results.
    @param run_set_id: An optional identifier of this set of results.
    """
    logging.info("    %s", resultFile)
    url = util.make_url(resultFile)

    parse = ElementTree.ElementTree().parse
    try:
        with util.open_url_seekable(url, mode="rb") as f:
            try:
                try:
                    resultElem = parse(typing.cast(typing.IO, gzip.GzipFile(fileobj=f)))
                except OSError:
                    f.seek(0)
                    resultElem = parse(bz2.BZ2File(f))
            except OSError:
                f.seek(0)
                resultElem = parse(f)
    except OSError as e:
        handle_error("Could not read result file %s: %s", resultFile, e)
    except ElementTree.ParseError as e:
        handle_error("Result file %s is invalid: %s", resultFile, e)

    if resultElem.tag not in ["result", "test"]:
        handle_error(
            f"XML file '{resultFile}' with benchmark results seems to be invalid.\n"
            "The root element of the file is not named 'result' or 'test'.\n"
            "If you want to run a table-definition file,\n"
            "you should use the option '-x' or '--xml'."
        )

    if ignore_errors and "error" in resultElem.attrib:
        logging.warning(
            'Ignoring file "%s" because of error: %s',
            resultFile,
            resultElem.attrib["error"],
        )
        return None

    if run_set_id is not None:
        for sourcefile in _get_run_tags_from_xml(resultElem):
            sourcefile.set("runset", run_set_id)

    insert_logfile_names(resultFile, resultElem)
    return resultElem


def insert_logfile_names(resultFile, resultElem):
    # get folder of logfiles (truncate end of XML file name and append .logfiles instead)
    log_folder = resultFile[0 : resultFile.rfind(".results.")] + ".logfiles/"

    # append begin of filename
    runSetName = resultElem.get("name")
    if runSetName is not None:
        blockname = resultElem.get("block")
        if blockname is None:
            log_folder += runSetName + "."
        elif blockname == runSetName:
            pass  # real runSetName is empty
        else:
            assert runSetName.endswith("." + blockname)
            runSetName = runSetName[: -(1 + len(blockname))]  # remove last chars
            log_folder += runSetName + "."

    # for each file: append original filename and insert log_file_name into sourcefileElement
    for sourcefile in _get_run_tags_from_xml(resultElem):
        if "logfile" in sourcefile.attrib:
            log_file = urllib.parse.urljoin(resultFile, sourcefile.get("logfile"))
        else:
            log_file = f"{log_folder}{os.path.basename(sourcefile.get('name'))}.log"
        sourcefile.set("logfile", log_file)


def apply_task_list(runset_results, tasks):
    """
    Set the results of all RunSetResult elements so that they contain the same tasks
    in the same order. For missing tasks a dummy element is inserted.
    Returns the number of missing run results.
    """
    missing = 0
    for runset in runset_results:
        # create mapping from id to RunResult object
        dic = {run_result.task_id: run_result for run_result in runset.results}
        assert len(dic) == len(runset.results)
        runset.results = []  # clear and repopulate results
        for task in tasks:
            run_result = dic.get(task)
            if run_result is None:
                logging.debug("    No result for task %s in '%s'.", task, runset)
                missing += 1
                # create an empty dummy element
                run_result = RunResult(
                    task,
                    None,
                    "empty",  # special category for tables
                    None,
                    None,
                    runset.columns,
                    [None] * len(runset.columns),
                )
            runset.results.append(run_result)
    return missing


class RunResult(object):
    """
    The class RunResult contains the results of a single verification run.
    """

    def __init__(
        self,
        task_id,
        status,
        category,
        score,
        log_file,
        columns,
        values,
        columns_relevant_for_diff=set(),
        sourcefiles_exist=True,
    ):
        assert len(columns) == len(values)
        self.task_id = task_id
        self.sourcefiles_exist = sourcefiles_exist
        self.status = status
        self.log_file = log_file
        self.columns = columns
        self.values = values
        self.category = category
        self.score = score
        self.columns_relevant_for_diff = columns_relevant_for_diff

    @staticmethod
    def create_from_xml(
        sourcefileTag,
        get_value_from_logfile,
        listOfColumns,
        correct_only,
        log_zip_cache,
        columns_relevant_for_diff,
        result_file_or_url,
    ):
        """
        This function collects the values from one run.
        Only columns that should be part of the table are collected.
        """

        def read_logfile_lines(log_file):
            if not log_file:
                return []
            log_file_url = util.make_url(log_file)
            url_parts = urllib.parse.urlparse(log_file_url, allow_fragments=False)
            log_zip_path = os.path.dirname(url_parts.path) + ".zip"
            log_zip_url = urllib.parse.urlunparse(
                (
                    url_parts.scheme,
                    url_parts.netloc,
                    log_zip_path,
                    url_parts.params,
                    url_parts.query,
                    url_parts.fragment,
                )
            )
            path_in_zip = urllib.parse.unquote(
                # os.path.relpath creates os-dependant paths, but windows separators can produce errors with zipfile lib
                util.fix_path_if_on_windows(
                    os.path.relpath(url_parts.path, os.path.dirname(log_zip_path))
                )
            )
            if log_zip_url.startswith("file:///") and not log_zip_path.startswith("/"):
                # Replace file:/// with file: for relative paths,
                # otherwise opening fails.
                log_zip_url = "file:" + log_zip_url[8:]

            try:
                with util.open_url_seekable(log_file_url, "rt") as logfile:
                    return logfile.readlines()
            except OSError:
                try:
                    if log_zip_url not in log_zip_cache:
                        log_zip_cache[log_zip_url] = zipfile.ZipFile(
                            util.open_url_seekable(log_zip_url, "rb")
                        )
                    log_zip = log_zip_cache[log_zip_url]

                    try:
                        with io.TextIOWrapper(log_zip.open(path_in_zip)) as logfile:
                            return logfile.readlines()
                    except KeyError:
                        logging.warning(
                            "Could not find logfile '%s' in archive '%s'.",
                            log_file,
                            log_zip_url,
                        )
                        return []

                except OSError:
                    logging.warning(
                        "Could not find logfile '%s' nor log archive '%s'.",
                        log_file,
                        log_zip_url,
                    )
                    return []

        sourcefiles = sourcefileTag.get("files")
        if sourcefiles:
            if not sourcefiles.startswith("["):
                raise AssertionError("Unknown format for files tag:")
            sourcefiles_exist = any(s.strip() for s in sourcefiles[1:-1].split(","))
        else:
            sourcefiles_exist = False

        task_name = sourcefileTag.get("name")
        if sourcefiles_exist:
            # task_name is a path
            task_name = normalize_path(task_name, result_file_or_url)

        prop, expected_result = get_property_of_task(
            task_name,
            result_file_or_url,
            sourcefileTag.get("properties"),
            sourcefileTag.get("propertyFile"),
            sourcefileTag.get("expectedVerdict"),
        )
        witness_category = util.get_column_value(sourcefileTag, "witness-category")
        task_id = TaskId(
            task_name,
            prop,
            expected_result,
            witness_category,
            sourcefileTag.get("runset"),
        )

        status = util.get_column_value(sourcefileTag, "status", "")
        category = util.get_column_value(sourcefileTag, "category")
        if not category:
            if status:  # only category missing
                category = result.CATEGORY_MISSING
            else:  # probably everything is missing, special category for tables
                category = "aborted"

        score = None
        if prop:
            score = prop.compute_score(category, status, witness_category)
        logfileLines = None

        values = []

        for column in listOfColumns:  # for all columns that should be shown
            value = None  # default value
            if column.title.lower() == "status":
                value = status

            elif not correct_only or category == result.CATEGORY_CORRECT:
                if not column.pattern or column.href:
                    # collect values from XML
                    value = util.get_column_value(sourcefileTag, column.title)

                else:  # collect values from logfile
                    if logfileLines is None:  # cache content
                        logfileLines = read_logfile_lines(sourcefileTag.get("logfile"))

                    value = get_value_from_logfile(logfileLines, column.pattern)

            if column.title.lower() == "score" and value is None and score is not None:
                # If no score column exists in the xml, take the internally computed score,
                # if available
                value = str(score)
            values.append(value)

        return RunResult(
            task_id,
            status,
            category,
            score,
            sourcefileTag.get("logfile"),
            listOfColumns,
            values,
            columns_relevant_for_diff,
            sourcefiles_exist=sourcefiles_exist,
        )


class Row(object):
    """
    The class Row contains all the results for one sourcefile (a list of RunResult instances).
    It is identified by the name of the source file and optional additional data
    (such as the property).
    It corresponds to one complete row in the final tables.
    """

    def __init__(self, results):
        assert results
        self.results = results
        self.id = results[0].task_id
        self.has_sourcefile = results[0].sourcefiles_exist
        assert (
            len({r.task_id for r in results}) == 1
        ), "not all results are for same task"

    def set_relative_path(self, common_prefix, base_dir):
        """
        generate output representation of rows
        """
        self.short_filename = self.id.name.replace(common_prefix, "", 1)


def get_property_of_task(
    task_name, base_path, property_string, property_file, expected_result
):
    if property_string is None:
        return (None, None)

    if property_file:
        property_file = normalize_path(property_file, base_path)
        try:
            prop = result.Property.create(property_file)
        except OSError as e:
            logging.debug("Cannot read property file %s: %s", property_file, e)
            prop = result.Property(property_file, False, property_string)

        if expected_result is not None:
            expected_result = result.ExpectedResult.from_str(expected_result)

        return (prop, expected_result)

    if task_name.endswith(".yml"):
        # try to find property file of task and create Property object
        try:
            task_template = model.load_task_definition_file(task_name)
            for prop_dict in task_template.get("properties", []):
                if "property_file" in prop_dict:
                    expanded = benchexec.util.expand_filename_pattern(
                        prop_dict["property_file"], os.path.dirname(task_name)
                    )
                    if len(expanded) == 1:
                        prop = result.Property.create(expanded[0])
                        if prop.name == property_string:
                            expected_result = prop_dict.get("expected_verdict")
                            if isinstance(expected_result, bool):
                                expected_result = result.ExpectedResult(
                                    expected_result, prop_dict.get("subproperty")
                                )
                            else:
                                expected_result = None
                            return (prop, expected_result)
        except BenchExecException as e:
            logging.debug("Could not load task-template file %s: %s", task_name, e)

    return (result.Property(None, False, property_string), None)


def rows_to_columns(rows):
    """
    Convert a list of Rows into a column-wise list of list of RunResult
    """
    return zip(*[row.results for row in rows])


def get_rows(runSetResults):
    """
    Create list of rows with all data. Each row consists of several RunResults.
    """
    rows = []
    for task_results in zip(*(runset.results for runset in runSetResults)):
        rows.append(Row(task_results))

    return rows


def filter_rows_with_differences(rows):
    """
    Find all rows with differences in the status column.
    """
    if not rows:
        # empty table
        return []
    if len(rows[0].results) == 1:
        # table with single column
        return []

    def get_index_of_column(name, cols):
        assert cols, f"Cannot look for column '{name}' in empy column list"
        for i in range(0, len(cols)):
            if cols[i].title == name:
                return i
        assert False, f"Column '{name}' not found in columns '{cols}'"

    def all_equal_result(listOfResults):
        relevant_columns = set()
        for res in listOfResults:
            for relevant_column in res.columns_relevant_for_diff:
                relevant_columns.add(relevant_column)
        if len(relevant_columns) == 0:
            relevant_columns.add("status")

        status = []
        for col in relevant_columns:
            # It's necessary to search for the index of a column every time
            # because they can differ between results
            status.append(
                {
                    res.values[get_index_of_column(col, res.columns)]
                    for res in listOfResults
                    if res.values
                }
            )

        return functools.reduce(lambda x, y: x and (len(y) <= 1), status, True)

    rowsDiff = [row for row in rows if not all_equal_result(row.results)]

    if len(rowsDiff) == 0:
        logging.info("---> NO DIFFERENCE FOUND IN SELECTED COLUMNS")
    elif len(rowsDiff) == len(rows):
        logging.info(
            "---> DIFFERENCES FOUND IN ALL ROWS, NO NEED TO CREATE DIFFERENCE TABLE"
        )
        return []
    else:
        logging.info("The difference table will have %s rows.", len(rowsDiff))

    return rowsDiff


def format_run_set_attributes_nicely(runSetResults):
    """Replace the attributes of each RunSetResult with nicely formatted strings."""
    for runSetResult in runSetResults:
        for key in runSetResult.attributes:
            values = runSetResult.attributes[key]
            if key == "turbo":
                turbo_values = list(set(values))
                if len(turbo_values) > 1:
                    turbo = "mixed"
                elif turbo_values[0] == "true":
                    turbo = "enabled"
                elif turbo_values[0] == "false":
                    turbo = "disabled"
                else:
                    turbo = None
                runSetResult.attributes["turbo"] = (
                    f", Turbo Boost: {turbo}" if turbo else ""
                )

            elif key == "timelimit":

                def fix_unit_display(value):
                    if len(value) >= 2 and value[-1] == "s" and value[-2] != " ":
                        return value[:-1] + " s"
                    return value

                runSetResult.attributes[key] = util.prettylist(
                    map(fix_unit_display, values)
                )

            elif key == "memlimit" or key == "ram":

                def round_to_MB(value):
                    number, unit = util.split_number_and_unit(value)
                    if unit and unit != "B":
                        return value
                    try:
                        return f"{int(number) / _BYTE_FACTOR / _BYTE_FACTOR:.0f} MB"
                    except ValueError:
                        return value

                runSetResult.attributes[key] = util.prettylist(map(round_to_MB, values))

            elif key == "freq":

                def round_to_MHz(value):
                    number, unit = util.split_number_and_unit(value)
                    if unit and unit != "Hz":
                        return value
                    try:
                        return f"{int(number) / 1000 / 1000:.0f} MHz"
                    except ValueError:
                        return value

                runSetResult.attributes[key] = util.prettylist(
                    map(round_to_MHz, values)
                )

            elif key == "host":
                runSetResult.attributes[key] = util.prettylist(
                    util.merge_entries_with_common_prefixes(values)
                )

            else:
                runSetResult.attributes[key] = util.prettylist(values)

    # compute nice name of each run set for displaying
    firstBenchmarkName = runSetResults[0].attributes["benchmarkname"]
    allBenchmarkNamesEqual = all(
        r.attributes["benchmarkname"] == firstBenchmarkName for r in runSetResults
    )

    for runSetResult in runSetResults:
        benchmarkName = runSetResult.attributes["benchmarkname"]
        name = runSetResult.attributes["name"]

        if not name:
            niceName = benchmarkName
        elif allBenchmarkNamesEqual:
            niceName = name
        else:
            niceName = f"{benchmarkName}.{name}"

        runSetResult.attributes["niceName"] = niceName


def select_relevant_id_columns(rows):
    """
    Find out which of the entries in Row.id are equal for all given rows.
    @return: A list of True/False values according to whether the i-th part of the id is always equal.
    """
    relevant_id_columns = [True]  # first column (file name) is always relevant
    if rows:
        prototype_id = rows[0].id
        for column in range(1, len(prototype_id)):
            all_equal = all(row.id[column] == prototype_id[column] for row in rows)
            relevant_id_columns.append(not all_equal)
    return relevant_id_columns


def compute_stats(rows, run_set_results, use_local_summary, correct_only):
    result_cols = list(rows_to_columns(rows))  # column-wise
    all_column_stats = list(
        parallel.map(
            statistics.get_stats_of_run_set,
            result_cols,
            [correct_only] * len(result_cols),
        )
    )

    if use_local_summary:
        for run_set_result, run_set_stats in zip(run_set_results, all_column_stats):
            statistics.add_local_summary_statistics(run_set_result, run_set_stats)

    return all_column_stats


def get_regression_count(rows, ignoreFlappingTimeouts):  # for options.dump_counts
    """Count the number of regressions, i.e., differences in status of the two right-most results
    where the new one is not "better" than the old one.
    Any change in status between error, unknown, and wrong result is a regression.
    Different kind of errors or wrong results are also a regression.
    """

    def status_is(run_result, status):
        # startswith is used because status can be "TIMEOUT (TRUE)" etc., which count as "TIMEOUT"
        return run_result.status and run_result.status.startswith(status)

    def any_status_is(run_results, status):
        for run_result in run_results:
            if status_is(run_result, status):
                return True
        return False

    regressions = 0
    for row in rows:
        if len(row.results) < 2:
            return 0  # no regressions at all with only one run

        # "new" and "old" are the latest two results
        new = row.results[-1]
        old = row.results[-2]

        if new.category == result.CATEGORY_CORRECT:
            continue  # no regression if result is correct

        if new.status == old.status:
            continue  # no regression if result is the same as before
        if status_is(new, "TIMEOUT") and status_is(old, "TIMEOUT"):
            continue  # no regression if both are some form of timeout
        if status_is(new, "OUT OF MEMORY") and status_is(old, "OUT OF MEMORY"):
            continue  # same for OOM

        if (
            ignoreFlappingTimeouts
            and status_is(new, "TIMEOUT")
            and any_status_is(row.results[:-2], "TIMEOUT")
        ):
            continue  # flapping timeout because any of the older results is also a timeout

        regressions += 1

    return regressions


def get_counts(rows):  # for options.dump_counts
    countsList = []

    for runResults in rows_to_columns(rows):
        counts = collections.Counter(runResult.category for runResult in runResults)
        countsList.append(
            (
                counts[result.CATEGORY_CORRECT],
                counts[result.CATEGORY_WRONG],
                counts[result.CATEGORY_UNKNOWN]
                + counts[result.CATEGORY_ERROR]
                + counts[None],  # for rows without a result
            )
        )

    return countsList


def create_tables(
    name, runSetResults, rows, rowsDiff, outputPath, outputFilePattern, options
):
    """
    Create tables and write them to files.
    @return a list of futures to allow waiting for completion
    """

    # get common folder of sourcefiles
    # os.path.commonprefix can return a partial path component (does not truncate on /)
    common_prefix = os.path.commonprefix([r.id.name for r in rows])
    separator = "/" if "://" in common_prefix else os.sep
    common_prefix = common_prefix[: common_prefix.rfind(separator) + 1]
    for row in rows:
        Row.set_relative_path(row, common_prefix, outputPath)

    # Ugly because this overwrites the entries in the attributes of RunSetResult,
    # but we don't need them anymore and this is the easiest way
    format_run_set_attributes_nicely(runSetResults)

    data = types.SimpleNamespace(
        run_sets=runSetResults,
        relevant_id_columns=select_relevant_id_columns(rows),
        output_path=outputPath,
        common_prefix=common_prefix,
        options=options,
    )

    futures = []

    def write_table(table_type, title, rows, use_local_summary):
        local_data = types.SimpleNamespace(title=title, rows=rows)

        # calculate statistics if necessary
        if not options.format == ["csv"]:
            local_data.stats = compute_stats(
                rows, runSetResults, use_local_summary, options.correct_only
            )

        for template_format in options.format or DEFAULT_TEMPLATE_FORMATS:
            if outputFilePattern == "-":
                outfile = None
                logging.info(
                    "Writing %s to stdout...", template_format.upper().ljust(4)
                )
            else:
                file_extension = re.sub("[^a-zA-Z]", ".", string=template_format)
                outfile = os.path.join(
                    outputPath,
                    outputFilePattern.format(
                        name=name, type=table_type, ext=file_extension
                    ),
                )
                logging.info(
                    "Writing %s into %s ...", template_format.upper().ljust(4), outfile
                )

            futures.append(
                parallel.submit(
                    write_table_in_format,
                    template_format,
                    outfile,
                    **data.__dict__,
                    **local_data.__dict__,
                )
            )

    # write normal tables
    write_table(
        "table",
        name,
        rows,
        use_local_summary=(not options.correct_only and not options.common),
    )

    # write difference tables
    if rowsDiff:
        write_table("diff", name + " differences", rowsDiff, use_local_summary=False)

    return futures


def write_csv_table(
    out, run_sets, rows, common_prefix, relevant_id_columns, sep="\t", **kwargs
):
    num_id_columns = relevant_id_columns[1:].count(True)

    def write_head_line(
        name, values, value_repetitions=itertools.repeat(1)  # noqa: B008
    ):
        if any(values):
            # name may contain paths, so standardize the output across OSs
            out.write(util.fix_path_if_on_windows(name))
            for i in range(num_id_columns):  # noqa: B007
                out.write(sep)
            for value, count in zip(values, value_repetitions):
                for i in range(count):  # noqa: B007
                    out.write(sep)
                    if value:
                        out.write(value)
            out.write("\n")

    write_head_line(
        "tool",
        ["{tool} {version}".format_map(run_set.attributes) for run_set in run_sets],
        [len(run_set.columns) for run_set in run_sets],
    )
    write_head_line(
        "run set",
        [run_set.attributes.get("niceName") for run_set in run_sets],
        [len(run_set.columns) for run_set in run_sets],
    )
    write_head_line(
        common_prefix,
        [column.format_title() for run_set in run_sets for column in run_set.columns],
    )

    for row in rows:
        # row.short_filename may contain paths, so standardize the output across OSs
        out.write(util.fix_path_if_on_windows(row.short_filename))
        for row_id, is_relevant in zip(row.id[1:], relevant_id_columns[1:]):
            if is_relevant:
                out.write(sep)
                if row_id is not None:
                    out.write(str(row_id))
        for run_result in row.results:
            for value, column in zip(run_result.values, run_result.columns):
                out.write(sep)
                out.write(column.format_value(value or "", "csv"))
        out.write("\n")


def write_table_in_format(template_format, outfile, options, **kwargs):
    callback = {
        "csv": write_csv_table,
        "html": htmltable.write_html_table,
        "statistics-tex": statisticstex.write_tex_command_table,
    }[template_format]

    if outfile:
        # Force HTML file to be UTF-8 regardless of system encoding because it actually
        # declares itself to be UTF-8 in a meta tag.
        encoding = "utf-8" if template_format == "html" else None
        with open(outfile, "w", encoding=encoding) as out:
            callback(out, options=options, **kwargs)

        if options.show_table and template_format == "html":
            system = platform.system()
            try:
                if system == "Windows":
                    os.startfile(  # pytype: disable=module-attr # noqa: S606
                        os.path.normpath(outfile), "open"
                    )
                else:
                    cmd = "open" if system == "Darwin" else "xdg-open"
                    subprocess.Popen(
                        [cmd, outfile],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
            except OSError:
                pass

    else:
        callback(sys.stdout, options=options, **kwargs)


def basename_without_ending(file):
    name = os.path.basename(file)
    if name.endswith(".xml"):
        name = name[:-4]
    elif name.endswith(".xml.gz"):
        name = name[:-7]
    elif name.endswith(".xml.bz2"):
        name = name[:-8]
    return name


def create_argument_parser():
    parser = argparse.ArgumentParser(
        fromfile_prefix_chars="@",
        description="""Create tables with the results of one or more benchmark executions.
           Command-line parameters can additionally be read from a file if file name prefixed with '@' is given as argument.
           Part of BenchExec: https://github.com/sosy-lab/benchexec/""",
    )

    parser.add_argument(
        "tables",
        metavar="RESULT",
        type=str,
        nargs="*",
        help="XML file with the results from the benchmark script",
    )
    parser.add_argument(
        "-x",
        "--xml",
        action="store",
        type=str,
        dest="xmltablefile",
        help="XML file with the table definition.",
    )
    parser.add_argument(
        "-o",
        "--outputpath",
        action="store",
        type=str,
        dest="outputPath",
        help="Output path for the tables. If '-', the tables are written to stdout.",
    )
    parser.add_argument(
        "-n",
        "--name",
        action="store",
        type=str,
        dest="output_name",
        help="Base name of the created output files.",
    )
    parser.add_argument(
        "--ignore-erroneous-benchmarks",
        action="store_true",
        dest="ignore_errors",
        help="Ignore incomplete result files or results where the was an error during benchmarking.",
    )
    parser.add_argument(
        "-d",
        "--dump",
        action="store_true",
        dest="dump_counts",
        help="Print summary statistics for regressions and the good, bad, and unknown counts.",
    )
    parser.add_argument(
        "--ignore-flapping-timeout-regressions",
        action="store_true",
        dest="ignoreFlappingTimeouts",
        help="For the regression-count statistics, do not count regressions to timeouts if the file already had timeouts before.",
    )
    parser.add_argument(
        "-f",
        "--format",
        action="append",
        choices=TEMPLATE_FORMATS,
        help="Which format to generate (HTML, CSV or TEX). Can be specified multiple times. If not specified, HTML and CSV are generated.",
    )
    parser.add_argument(
        "-c",
        "--common",
        action="store_true",
        dest="common",
        help="Put only rows into the table for which all benchmarks contain results.",
    )
    parser.add_argument(
        "--no-diff",
        action="store_false",
        dest="write_diff_table",
        help="Do not output a table with result differences between benchmarks.",
    )
    parser.add_argument(
        "--correct-only",
        action="store_true",
        dest="correct_only",
        help="Clear all results (e.g., time) in cases where the result was not correct.",
    )
    parser.add_argument(
        "--all-columns",
        action="store_true",
        dest="all_columns",
        help="Show all columns in tables, including those that are normally hidden.",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        dest="show_table",
        help="Open the produced HTML table(s) in the default browser.",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Do not show informational messages, only warnings.",
    )

    def handle_initial_table_state(value):
        value = value.lstrip("#")
        if not value.startswith("/"):
            raise argparse.ArgumentTypeError(
                f"Invalid value '{value}', needs to start with /"
            )
        return value

    parser.add_argument(
        "--initial-table-state",
        action="store",
        type=handle_initial_table_state,
        help="Set initial state of HTML table, e.g., if another tab should be shown "
        "by default. Valid values can be copied from the URL part after '#' of a table "
        "when the table is in the desired state. (Example: '/table')",
    )
    parser.add_argument(
        "--version", action="version", version="%(prog)s " + __version__
    )
    return parser


def sigint_handler(*args, **kwargs):
    # Use SystemExit instead of KeyboardInterrupt to avoid ugly stack traces for each worker
    sys.exit(1)


def get_max_worker_count():
    """Calculate maximum number of worker processes to use."""
    try:
        cpu_count = os.cpu_count() or 1
    except AttributeError:
        cpu_count = 1

    try:
        import resource

        fd_limit = resource.getrlimit(resource.RLIMIT_NOFILE)[1]
        # increase soft limit to hard limit
        resource.setrlimit(resource.RLIMIT_NOFILE, (fd_limit, fd_limit))
        # for each worker some open fds are needed, so use heuristic limit
        max_workers = fd_limit // 4
    except ImportError:  # Windows
        # it seems there is some rather low hard limit
        # https://stackoverflow.com/q/870173/396730
        max_workers = 128

    # Use up to cpu_count*2 workers because some tasks are I/O bound,
    # but limit the number of worker to avoid too many open files.
    return min(cpu_count * 2, max_workers)


def get_preferred_mp_context():
    import multiprocessing

    method = "spawn" if "spawn" in multiprocessing.get_all_start_methods() else None
    return multiprocessing.get_context(method=method)


def setup_process(options):
    """Perform basic process setup, e.g., logging."""
    signal.signal(signal.SIGINT, sigint_handler)
    benchexec.util.setup_logging(
        fmt="%(levelname)s: %(message)s",
        level=logging.WARNING if options.quiet else logging.INFO,
    )


def main(args=None):
    if sys.version_info < (3,):
        sys.exit("table-generator needs Python 3 to run.")

    arg_parser = create_argument_parser()
    options = arg_parser.parse_args((args or sys.argv)[1:])

    setup_process(options)

    global parallel
    import concurrent.futures

    parallel = concurrent.futures.ProcessPoolExecutor(
        max_workers=get_max_worker_count(),
        mp_context=get_preferred_mp_context(),
        initializer=setup_process,
        initargs=(options,),
    )

    name = options.output_name
    outputPath = options.outputPath
    if outputPath == "-":
        # write to stdout
        outputFilePattern = "-"
        outputPath = "."
    else:
        outputFilePattern = "{name}.{type}.{ext}"

    if options.xmltablefile:
        try:
            table_definition = parse_table_definition_file(options.xmltablefile)

            if table_definition_lists_result_files(table_definition):
                if options.tables:
                    arg_parser.error(
                        f"Invalid additional arguments '{' '.join(options.tables)}'."
                    )

                runSetResults = load_results_from_table_definition(
                    table_definition, options.xmltablefile, options
                )

            else:
                if not options.tables:
                    arg_parser.error(
                        "No result files given. Either list them on the command line "
                        "or with <result> tags in the table-definiton file."
                    )

                result_files = util.extend_file_list(options.tables)  # expand wildcards
                runSetResults = load_results_with_table_definition(
                    result_files, table_definition, options.xmltablefile, options
                )

        except util.TableDefinitionError as e:
            handle_error("Fault in %s: %s", options.xmltablefile, e)

        if not name:
            name = basename_without_ending(options.xmltablefile)

        if not outputPath:
            outputPath = os.path.dirname(options.xmltablefile)

    else:
        if options.tables:
            inputFiles = options.tables
        else:
            searchDir = outputPath or DEFAULT_OUTPUT_PATH
            logging.info("Searching result files in '%s'...", searchDir)
            inputFiles = [os.path.join(searchDir, "*.results*.xml")]

        inputFiles = util.extend_file_list(inputFiles)  # expand wildcards
        runSetResults = load_results(inputFiles, options)

        if len(inputFiles) == 1:
            if not name:
                name = basename_without_ending(inputFiles[0])
            if not outputFilePattern == "-":
                outputFilePattern = "{name}.{ext}"
        else:
            if not name:
                timestamp = time.strftime(
                    benchexec.util.TIMESTAMP_FILENAME_FORMAT, time.localtime()
                )
                name = f"{NAME_START}.{timestamp}"

        if inputFiles and not outputPath:
            path = os.path.dirname(inputFiles[0])
            if "://" not in path and all(
                path == os.path.dirname(file) for file in inputFiles
            ):
                outputPath = path
            else:
                outputPath = DEFAULT_OUTPUT_PATH

    if not outputPath:
        outputPath = "."

    runSetResults = [r for r in runSetResults if r is not None]
    if not runSetResults:
        handle_error("No benchmark results found.")

    logging.info("Merging results...")
    if options.common:
        task_list = util.find_common_elements(r.get_tasks() for r in runSetResults)
        if not task_list:
            logging.warning("No tasks are present in all benchmark results.")
    else:
        # merge list of tasks, so that all run sets contain the same tasks
        task_list = util.merge_lists(r.get_tasks() for r in runSetResults)
    # make sure that all run sets contain exactly the same tasks in the same order
    missing_run_results = apply_task_list(runSetResults, task_list)

    rows = get_rows(runSetResults)
    logging.info(
        "The resulting table will have %s rows and %s columns (in %s run sets).",
        len(rows),
        sum(len(runset.columns) for runset in runSetResults),
        len(runSetResults),
    )
    if missing_run_results:
        logging.info(
            "%s run results were not found in the input files "
            "and will be empty in the table (%s run results are present).",
            missing_run_results,
            len(rows) * len(runSetResults) - missing_run_results,
        )
    if not rows:
        handle_error("No results found, no tables produced.")
    rowsDiff = filter_rows_with_differences(rows) if options.write_diff_table else []

    logging.info("Generating table...")
    if not os.path.isdir(outputPath) and not outputFilePattern == "-":
        os.makedirs(outputPath)
    futures = create_tables(
        name, runSetResults, rows, rowsDiff, outputPath, outputFilePattern, options
    )

    if options.dump_counts:  # print some stats for Buildbot
        print("REGRESSIONS", get_regression_count(rows, options.ignoreFlappingTimeouts))

        countsList = get_counts(rows)
        print("STATS")
        for counts in countsList:
            print(*counts)

    for f in futures:
        f.result()  # to get any exceptions that may have occurred
    logging.info("done")

    parallel.shutdown(wait=True)


if __name__ == "__main__":
    sys.exit(main())
